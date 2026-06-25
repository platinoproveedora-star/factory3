from __future__ import annotations
import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, identity_row, insert_event, money, reserve_folio, resolve_billing_context, today_iso  # noqa: E402

_SKILLS_ROOT = Path(__file__).resolve().parents[2]
_VALID_METHODS = {"cash", "transfer", "deposit", "card", "check", "other"}
_AUTO_CONFIRM = {"cash", "card"}


class ErpBillingAnticipoCreateService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        customer_name = blank(context.get("customer_name"))
        if not customer_name:
            return {"ok": False, "error": "customer_name requerido"}
        amount = money(context.get("amount"))
        if amount <= 0:
            return {"ok": False, "error": "amount debe ser mayor a 0"}
        payment_method = str(context.get("payment_method") or "").strip()
        if payment_method not in _VALID_METHODS:
            return {"ok": False, "error": f"payment_method invalido. Validos: {sorted(_VALID_METHODS)}"}

        row = {
            **identity_row(ctx),
            "customer_id": blank(context.get("customer_id")),
            "customer_name": customer_name,
            "amount": amount,
            "unapplied_amount": amount,
            "payment_method": payment_method,
            "payment_date": str(context.get("payment_date") or today_iso()),
            "destination_money_account_id": blank(context.get("destination_money_account_id")),
            "bank_name": blank(context.get("bank_name")),
            "reference": blank(context.get("reference")),
            "tracking_key": blank(context.get("tracking_key")),
            "receipt_file_url": blank(context.get("receipt_file_url")),
            "notes": blank(context.get("notes")),
            "status": "disponible",
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se registro anticipo", "data": {"anticipo": {"folio": "ANT-DRYRUN", **row}}}

        folio_result = reserve_folio(ctx, "billing_anticipos", "ANT")
        if not folio_result.get("ok"):
            return folio_result
        row["folio"] = folio_result["data"]["folio"]

        result = SupabaseClient(ctx).rest_insert("billing_anticipos", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        anticipo = data[0] if isinstance(data, list) and data else data
        self._record_bank_movement(context, ctx, anticipo, amount, payment_method)
        insert_event(ctx, "anticipo_created", {"anticipo_id": anticipo.get("id"), "folio": anticipo.get("folio"), "amount": amount}, False)
        return {"ok": True, "data": {"anticipo": anticipo}}

    def _record_bank_movement(self, context: dict, ctx: dict, anticipo: dict, amount: float, method: str) -> None:
        account_id = blank(context.get("destination_money_account_id"))
        if not account_id:
            return
        banks_schema = str(context.get("banks_schema") or "").strip()
        if not banks_schema:
            return
        service_path = _SKILLS_ROOT / "vertical_erp_banks" / "erp_banks_movement_record" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_banks_movement_record_service", service_path)
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ErpBanksMovementRecordService().ejecutar({
            **context,
            "schema": banks_schema,
            "dry_run": False,
            "account_id": account_id,
            "movement_type": "entrada",
            "source_type": "anticipo",
            "source_id": anticipo.get("id"),
            "source_folio": anticipo.get("folio"),
            "amount": amount,
            "movement_date": anticipo.get("payment_date"),
            "notes": f"Anticipo {anticipo.get('folio')} - {anticipo.get('customer_name') or ''}".strip(" -"),
            "metadata": {"billing_schema": ctx.get("schema"), "payment_method": method},
        })
