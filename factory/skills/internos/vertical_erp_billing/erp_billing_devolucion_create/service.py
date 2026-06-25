from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, insert_event, money, reserve_folio, resolve_billing_context, sales_context  # noqa: E402


class ErpBillingDevolucionCreateService:
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

        sales_folio = blank(context.get("sales_folio") or context.get("document_folio"))
        sales_document_id = blank(context.get("sales_document_id") or context.get("document_id"))

        # Verificar que la remision existe si se proporciona
        sales_schema = None
        if sales_folio or sales_document_id:
            sales_ctx_result = sales_context(ctx)
            if sales_ctx_result.get("ok"):
                sales_ctx = sales_ctx_result["data"]
                sales_schema = sales_ctx["schema"]
                filters = {"id": sales_document_id} if sales_document_id else {"folio": sales_folio}
                doc = fetch_one(SupabaseClient(sales_ctx), "sales_documents", filters, "id,folio,customer_name_snapshot")
                if not doc:
                    return {"ok": False, "error": "remision no encontrada"}
                if not sales_document_id:
                    sales_document_id = doc["id"]
                if not sales_folio:
                    sales_folio = doc.get("folio")

        row = {
            **identity_row(ctx),
            "customer_id": blank(context.get("customer_id")),
            "customer_name": customer_name,
            "sales_schema": sales_schema,
            "sales_document_id": sales_document_id,
            "sales_folio": sales_folio,
            "amount": amount,
            "reason": blank(context.get("reason") or context.get("motivo")),
            "status": "pendiente",
            "notes": blank(context.get("notes")),
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se registro devolucion", "data": {"devolucion": {"folio": "DEV-DRYRUN", **row}}}

        folio_result = reserve_folio(ctx, "billing_devoluciones", "DEV")
        if not folio_result.get("ok"):
            return folio_result
        row["folio"] = folio_result["data"]["folio"]

        result = SupabaseClient(ctx).rest_insert("billing_devoluciones", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        devolucion = data[0] if isinstance(data, list) and data else data
        insert_event(ctx, "devolucion_created", {"devolucion_id": devolucion.get("id"), "folio": devolucion.get("folio"), "amount": amount}, False)
        return {"ok": True, "data": {"devolucion": devolucion}}
