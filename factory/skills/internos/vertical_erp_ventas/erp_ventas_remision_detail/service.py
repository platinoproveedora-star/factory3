from __future__ import annotations

from factory.engine import SupabaseClient


class ErpVentasRemisionDetailService:
    def ejecutar(self, context: dict) -> dict:
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}

        ctx = {**context, "schema": "uc101_proy002"}
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        doc_res = SupabaseClient(ctx).rest_select(
            "sales_documents",
            filters=filters,
            select="id,folio,external_folio,customer_id,customer_name_snapshot,status,document_date,delivery_address,subtotal,tax_total,total,balance_total,notes,created_at",
            limit=1,
        )
        if not doc_res.get("ok"):
            return doc_res
        docs = doc_res.get("data") or []
        if not docs:
            return {"ok": False, "error": "remision no encontrada"}
        doc = docs[0]

        items_res = SupabaseClient(ctx).rest_select(
            "sales_document_items",
            filters={"document_id": doc["id"]},
            select="id,folio,product_id,inventory_product_id,product_folio_snapshot,product_name_snapshot,description,quantity,unit,unit_price,lot_code,lot_cost_snapshot,avg_cost_snapshot,last_cost_snapshot,tax_rate,tax_amount,line_total,metadata,created_at",
            order="created_at.asc",
            limit=500,
        )
        if not items_res.get("ok"):
            return items_res
        return {"ok": True, "data": {"remision": doc, "items": items_res.get("data") or []}}
