from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, insert_event, money, reserve_folio, resolve_billing_context, today_iso  # noqa: E402

_SKILLS_ROOT = Path(__file__).resolve().parents[2]


VALID_METHODS = {"cash", "transfer", "deposit", "card", "check", "other"}
_AUTO_CONFIRM = {"cash", "card"}  # efectivo y terminal se confirman al instante


class ErpBillingPaymentCreateService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        payment_method = str(context.get("payment_method") or "").strip()
        amount = money(context.get("amount"))
        if payment_method not in VALID_METHODS:
            return {"ok": False, "error": "payment_method invalido"}
        if amount <= 0:
            return {"ok": False, "error": "amount debe ser mayor a 0"}

        collections_result = self._collections(ctx, context)
        if not collections_result.get("ok"):
            return collections_result
        collections = collections_result["data"]["collections"]
        collection = collections[0] if collections else None
        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        if collections:
            metadata = {
                **metadata,
                "collection_folios": [
                    {
                        "id": item.get("id"),
                        "folio": item.get("folio"),
                        "customer_id": item.get("customer_id"),
                        "customer_name": item.get("customer_name"),
                        "expected_amount": money(item.get("expected_amount")),
                        "balance_amount": money(item.get("balance_amount")),
                    }
                    for item in collections
                ],
            }
        receipt_file_url = blank(context.get("receipt_file_url") or context.get("document_file_url"))
        destination_bank_account_id = blank(context.get("destination_bank_account_id") or context.get("bank_account_id"))
        destination_billing_account_id = blank(context.get("destination_billing_money_account_id") or context.get("billing_money_account_id"))
        raw_destination_account_id = blank(context.get("destination_money_account_id"))
        if not destination_bank_account_id and not destination_billing_account_id:
            if str(context.get("banks_schema") or context.get("banks_supabase_schema") or "").strip():
                destination_bank_account_id = raw_destination_account_id
            else:
                destination_billing_account_id = raw_destination_account_id
        if destination_bank_account_id:
            metadata = {**metadata, "destination_bank_account_id": destination_bank_account_id}
        row = {
            **identity_row(ctx),
            "collection_folio_id": blank(context.get("collection_folio_id") or (collection or {}).get("id")),
            "collection_folio": blank(context.get("collection_folio") or (collection or {}).get("folio")),
            "customer_id": blank(context.get("customer_id") or (collection or {}).get("customer_id")),
            "customer_name": blank(context.get("customer_name") or (collection or {}).get("customer_name")),
            "payment_method": payment_method,
            "amount": amount,
            "unapplied_amount": amount,
            "payment_date": str(context.get("payment_date") or today_iso()),
            "source_money_account_id": blank(context.get("source_money_account_id")),
            "destination_money_account_id": destination_billing_account_id,
            "bank_name": blank(context.get("bank_name")),
            "sender_account": blank(context.get("sender_account")),
            "receiver_account": blank(context.get("receiver_account")),
            "tracking_key": blank(context.get("tracking_key") or context.get("rastreo")),
            "reference": blank(context.get("reference") or context.get("referencia")),
            "receipt_file_url": receipt_file_url,
            "receipt_file_path": blank(context.get("receipt_file_path") or context.get("document_file_path")),
            "receipt_file_bucket": blank(context.get("receipt_file_bucket") or context.get("document_file_bucket")),
            "ocr_status": str(context.get("ocr_status") or ("pending" if receipt_file_url else "not_required")).strip(),
            "validation_status": str(context.get("validation_status") or "manual").strip(),
            "confirmation_status": "confirmado" if payment_method in _AUTO_CONFIRM else "por_confirmar",
            "status": str(context.get("status") or "sin_aplicar").strip(),
            "notes": blank(context.get("notes")),
            "metadata": metadata,
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se registro pago", "data": {"payment": {"folio": "BPAY-DRYRUN", **row}}}

        folio_result = reserve_folio(ctx, "billing_payments", "BPAY")
        if not folio_result.get("ok"):
            return folio_result
        row["folio"] = folio_result["data"]["folio"]
        result = SupabaseClient(ctx).rest_insert("billing_payments", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        payment = data[0] if isinstance(data, list) and data else data
        insert_event(ctx, "payment_created", {"payment_id": payment.get("id"), "folio": payment.get("folio"), "amount": amount}, False)
        self._record_bank_movement(context, ctx, payment, amount)
        return {"ok": True, "data": {"payment": payment}}

    def _record_bank_movement(self, context: dict, ctx: dict, payment: dict, amount: float) -> None:
        account_id = blank(context.get("destination_bank_account_id") or context.get("bank_account_id") or context.get("destination_money_account_id"))
        account_folio = blank(context.get("destination_account_folio"))
        if not account_id and not account_folio:
            return
        banks_schema = str(context.get("banks_schema") or context.get("banks_supabase_schema") or "").strip()
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
            "banks_schema": banks_schema,
            "project_code": context.get("banks_project_code") or ctx.get("project_code"),
            "module_code": "banks",
            "dry_run": False,
            "account_id": account_id,
            "account_folio": account_folio,
            "movement_type": "entrada",
            "source_type": "pago",
            "source_id": payment.get("id"),
            "source_folio": payment.get("folio"),
            "amount": amount,
            "movement_date": payment.get("payment_date"),
            "notes": f"Pago {payment.get('folio')} - {payment.get('customer_name') or ''}".strip(" -"),
            "metadata": {"billing_schema": ctx.get("schema"), "payment_method": context.get("payment_method")},
        })

    def _collections(self, ctx: dict, context: dict) -> dict:
        raw_items = context.get("collection_folios")
        collections = []
        if isinstance(raw_items, list) and raw_items:
            for raw in raw_items:
                if not isinstance(raw, dict):
                    return {"ok": False, "error": "collection_folios debe ser una lista de objetos"}
                collection = self._collection(ctx, raw)
                if not collection:
                    return {"ok": False, "error": "folio de cobranza no encontrado"}
                collections.append(collection)
        else:
            collection = self._collection(ctx, context)
            if collection:
                collections.append(collection)

        customer_key = None
        for collection in collections:
            status = str(collection.get("status") or "").strip().lower()
            if status in {"cancelado", "cancelada", "pagada"}:
                return {"ok": False, "error": "no se puede registrar pago contra folios cancelados o pagados"}
            key = collection.get("customer_id") or collection.get("customer_name")
            if customer_key and key and customer_key != key:
                return {"ok": False, "error": "todos los folios del pago deben ser del mismo cliente"}
            customer_key = customer_key or key
        return {"ok": True, "data": {"collections": collections}}

    def _collection(self, ctx: dict, context: dict) -> dict | None:
        collection_id = blank(context.get("collection_folio_id"))
        collection_folio = blank(context.get("collection_folio") or context.get("folio"))
        if not collection_id and not collection_folio:
            return None
        filters = {"id": collection_id} if collection_id else {"folio": collection_folio}
        return fetch_one(SupabaseClient(ctx), "billing_collection_folios", filters, "id,folio,customer_id,customer_name,expected_amount,balance_amount,status")
