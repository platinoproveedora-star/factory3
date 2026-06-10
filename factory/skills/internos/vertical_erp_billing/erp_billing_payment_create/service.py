from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, insert_event, money, reserve_folio, resolve_billing_context, today_iso  # noqa: E402


VALID_METHODS = {"cash", "transfer", "deposit", "card", "check", "other"}


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

        collection = self._collection(ctx, context)
        receipt_file_url = blank(context.get("receipt_file_url") or context.get("document_file_url"))
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
            "destination_money_account_id": blank(context.get("destination_money_account_id")),
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
            "status": str(context.get("status") or "capturado").strip(),
            "notes": blank(context.get("notes")),
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
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
        return {"ok": True, "data": {"payment": payment}}

    def _collection(self, ctx: dict, context: dict) -> dict | None:
        collection_id = blank(context.get("collection_folio_id"))
        collection_folio = blank(context.get("collection_folio"))
        if not collection_id and not collection_folio:
            return None
        filters = {"id": collection_id} if collection_id else {"folio": collection_folio}
        return fetch_one(SupabaseClient(ctx), "billing_collection_folios", filters, "id,folio,customer_id,customer_name,balance_amount,status")
