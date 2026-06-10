from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, identity_row, insert_event, money, reserve_folio, resolve_billing_context, utc_now  # noqa: E402


VALID_TYPES = {"bank", "cash", "cash_box", "collector_cash", "card_terminal", "other"}


class ErpBillingMoneyAccountCreateService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        account_id = blank(context.get("id") or context.get("account_id"))
        account_type = str(context.get("account_type") or "cash").strip()
        account_name = str(context.get("account_name") or context.get("name") or "").strip()
        if account_type not in VALID_TYPES:
            return {"ok": False, "error": "account_type invalido"}
        if not account_name:
            return {"ok": False, "error": "account_name requerido"}

        row = {
            "account_type": account_type,
            "account_name": account_name,
            "bank_name": blank(context.get("bank_name")),
            "account_number_mask": blank(context.get("account_number_mask") or context.get("account_mask")),
            "holder_name": blank(context.get("holder_name")),
            "currency": str(context.get("currency") or "MXN").strip() or "MXN",
            "responsible_user": blank(context.get("responsible_user")),
            "status": str(context.get("status") or "active").strip() or "active",
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
        }
        if not account_id:
            row.update(identity_row(ctx))
            row["opening_balance"] = money(context.get("opening_balance"))
            row["current_balance"] = money(context.get("current_balance") if context.get("current_balance") is not None else row["opening_balance"])
        else:
            row["updated_at"] = utc_now()

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se guardo cuenta de dinero", "data": {"account": row}}

        db = SupabaseClient(ctx)
        if account_id:
            result = db.rest_update("billing_money_accounts", row, {"id": account_id})
        else:
            folio_result = reserve_folio(ctx, "billing_money_accounts", "BMA")
            if not folio_result.get("ok"):
                return folio_result
            row["folio"] = folio_result["data"]["folio"]
            result = db.rest_insert("billing_money_accounts", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        account = data[0] if isinstance(data, list) and data else data
        insert_event(ctx, "money_account_saved", {"account_id": account.get("id"), "folio": account.get("folio")}, False)
        return {"ok": True, "data": {"account": account}}
