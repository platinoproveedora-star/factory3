from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, insert_event, money, reserve_folio, resolve_billing_context, sales_context, utc_now  # noqa: E402


class ErpBillingAnticipoApplyService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        sales_ctx_result = sales_context(ctx)
        if not sales_ctx_result.get("ok"):
            return sales_ctx_result
        sales_ctx = sales_ctx_result["data"]

        anticipo_id = blank(context.get("anticipo_id") or context.get("anticipo_folio"))
        if not anticipo_id:
            return {"ok": False, "error": "anticipo_id o anticipo_folio requerido"}

        filters = {"id": anticipo_id} if len(anticipo_id) > 20 else {"folio": anticipo_id}
        anticipo = fetch_one(SupabaseClient(ctx), "billing_anticipos", filters)
        if not anticipo:
            return {"ok": False, "error": "anticipo no encontrado"}
        if anticipo.get("status") == "aplicado":
            return {"ok": False, "error": "el anticipo ya fue aplicado completamente"}

        doc_id = blank(context.get("sales_document_id") or context.get("document_id"))
        doc_folio = blank(context.get("sales_folio") or context.get("document_folio"))
        if not doc_id and not doc_folio:
            return {"ok": False, "error": "sales_document_id o sales_folio requerido"}
        doc_filters = {"id": doc_id} if doc_id else {"folio": doc_folio}
        document = fetch_one(SupabaseClient(sales_ctx), "sales_documents", doc_filters, "id,folio,total,paid_total,balance_total,status,customer_id,customer_name_snapshot")
        if not document:
            return {"ok": False, "error": "remision no encontrada"}

        unapplied = money(anticipo.get("unapplied_amount"))
        doc_balance = money(document.get("balance_total") if document.get("balance_total") is not None else document.get("total"))
        amount = money(context.get("amount_applied") if context.get("amount_applied") is not None else min(unapplied, doc_balance))

        if amount <= 0:
            return {"ok": False, "error": "amount_applied debe ser mayor a 0"}
        if amount > unapplied:
            return {"ok": False, "error": "amount_applied excede el saldo disponible del anticipo"}

        new_paid = money(document.get("paid_total")) + amount
        new_balance = max(money(document.get("total")) - new_paid, 0)
        doc_status = "pagada" if new_balance <= 0 else "parcial"
        new_unapplied = max(unapplied - amount, 0)
        anticipo_status = "aplicado" if new_unapplied <= 0 else "parcial"

        preview = {
            "anticipo_update": {"unapplied_amount": new_unapplied, "status": anticipo_status},
            "document_update": {"paid_total": new_paid, "balance_total": new_balance, "status": doc_status},
            "amount_applied": amount,
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se aplico anticipo", "data": preview}

        billing_db = SupabaseClient(ctx)
        sales_db = SupabaseClient(sales_ctx)

        # Insertar aplicacion en billing_payment_applications reutilizando la tabla
        folio_result = reserve_folio(ctx, "billing_payment_applications", "BAPP")
        if not folio_result.get("ok"):
            return folio_result
        application = {
            **identity_row(ctx),
            "folio": folio_result["data"]["folio"],
            "payment_id": anticipo["id"],
            "payment_folio": anticipo.get("folio"),
            "sales_schema": sales_ctx["schema"],
            "sales_document_id": document["id"],
            "sales_folio": document.get("folio"),
            "amount_applied": amount,
            "status": "aplicado",
            "metadata": {"source": "anticipo", "document_balance_after": new_balance, "document_status_after": doc_status},
        }
        app_result = billing_db.rest_insert("billing_payment_applications", application)
        if not app_result.get("ok"):
            return app_result

        sales_db.rest_update("sales_documents", {"paid_total": new_paid, "balance_total": new_balance, "status": doc_status, "updated_at": utc_now()}, {"id": document["id"]})
        billing_db.rest_update("billing_anticipos", {"unapplied_amount": new_unapplied, "status": anticipo_status, "updated_at": utc_now()}, {"id": anticipo["id"]})
        insert_event(ctx, "anticipo_applied", {"anticipo_id": anticipo["id"], "document_id": document["id"], "amount": amount}, False)
        return {"ok": True, "data": {**preview, "application_folio": folio_result["data"]["folio"]}}
