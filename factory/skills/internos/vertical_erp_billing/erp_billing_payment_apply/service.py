from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, insert_event, money, reserve_folio, resolve_billing_context, sales_context, utc_now  # noqa: E402


class ErpBillingPaymentApplyService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        sales_ctx_result = sales_context(ctx)
        if not sales_ctx_result.get("ok"):
            return sales_ctx_result
        sales_ctx = sales_ctx_result["data"]

        payment = self._payment(ctx, context)
        if not payment:
            return {"ok": False, "error": "payment_id/payment_folio requerido o no encontrado"}
        document = self._document(sales_ctx, context)
        if not document:
            return {"ok": False, "error": "sales_document_id/sales_folio requerido o no encontrado"}

        unapplied = money(payment.get("unapplied_amount") if payment.get("unapplied_amount") is not None else payment.get("amount"))
        current_balance = money(document.get("balance_total") if document.get("balance_total") is not None else document.get("total"))
        amount = money(context.get("amount_applied") if context.get("amount_applied") is not None else min(unapplied, current_balance))
        if amount <= 0:
            return {"ok": False, "error": "amount_applied debe ser mayor a 0"}
        if amount > unapplied:
            return {"ok": False, "error": "amount_applied excede el saldo no aplicado del pago"}

        new_paid = money(document.get("paid_total")) + amount
        new_balance = max(money(document.get("total")) - new_paid, 0)
        doc_status = "pagada" if new_balance <= 0 else "parcial"
        payment_unapplied = max(unapplied - amount, 0)
        payment_status = "aplicado" if payment_unapplied <= 0 else "parcial"
        application = {
            **identity_row(ctx),
            "payment_id": payment["id"],
            "payment_folio": payment.get("folio"),
            "sales_schema": sales_ctx["schema"],
            "sales_document_id": document["id"],
            "sales_folio": document.get("folio"),
            "amount_applied": amount,
            "status": "aplicado",
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
        }
        preview = {
            "application": {"folio": "BAPP-DRYRUN", **application},
            "document_update": {"paid_total": new_paid, "balance_total": new_balance, "status": doc_status},
            "payment_update": {"unapplied_amount": payment_unapplied, "status": payment_status},
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se aplico pago", "data": preview}

        billing_db = SupabaseClient(ctx)
        sales_db = SupabaseClient(sales_ctx)
        folio_result = reserve_folio(ctx, "billing_payment_applications", "BAPP")
        if not folio_result.get("ok"):
            return folio_result
        application["folio"] = folio_result["data"]["folio"]
        app_result = billing_db.rest_insert("billing_payment_applications", application)
        if not app_result.get("ok"):
            return app_result
        doc_result = sales_db.rest_update(
            "sales_documents",
            {"paid_total": new_paid, "balance_total": new_balance, "status": doc_status, "updated_at": utc_now()},
            {"id": document["id"]},
        )
        if not doc_result.get("ok"):
            return doc_result
        pay_result = billing_db.rest_update(
            "billing_payments",
            {"unapplied_amount": payment_unapplied, "status": payment_status, "updated_at": utc_now()},
            {"id": payment["id"]},
        )
        if not pay_result.get("ok"):
            return pay_result
        if payment.get("collection_folio_id"):
            billing_db.rest_update(
                "billing_collection_folios",
                {"collected_amount": new_paid, "balance_amount": new_balance, "status": doc_status, "payment_id": payment["id"], "updated_at": utc_now()},
                {"id": payment["collection_folio_id"]},
            )
        insert_event(ctx, "payment_applied", {"payment_id": payment["id"], "document_id": document["id"], "amount": amount}, False)
        app_data = app_result.get("data") or []
        application_saved = app_data[0] if isinstance(app_data, list) and app_data else app_data
        return {"ok": True, "data": {"application": application_saved, "document_update": doc_result.get("data"), "payment_update": pay_result.get("data")}}

    def _payment(self, ctx: dict, context: dict) -> dict | None:
        payment_id = blank(context.get("payment_id"))
        folio = blank(context.get("payment_folio") or context.get("folio"))
        if not payment_id and not folio:
            return None
        filters = {"id": payment_id} if payment_id else {"folio": folio}
        return fetch_one(SupabaseClient(ctx), "billing_payments", filters)

    def _document(self, sales_ctx: dict, context: dict) -> dict | None:
        doc_id = blank(context.get("sales_document_id") or context.get("document_id"))
        folio = blank(context.get("sales_folio") or context.get("document_folio"))
        if not doc_id and not folio:
            return None
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        return fetch_one(SupabaseClient(sales_ctx), "sales_documents", filters, "id,folio,total,paid_total,balance_total,status")
