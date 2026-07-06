from __future__ import annotations

from factory.engine import SupabaseClient


class ErpVentasPedidoDetailService:
    def ejecutar(self, context: dict) -> dict:
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}

        ctx = self._sales_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        doc_res = SupabaseClient(ctx).rest_select(
            "sales_documents",
            filters={**filters, "document_type": "eq.pedido"},
            select=(
                "id,folio,external_folio,parent_document_id,root_document_id,customer_id,"
                "customer_name_snapshot,customer_folio_snapshot,status,document_date,due_date,"
                "delivery_address,payment_method,city,city_quadrant,total_weight_kg,subtotal,"
                "tax_total,total,balance_total,notes,metadata,created_at,updated_at"
            ),
            limit=1,
        )
        if not doc_res.get("ok"):
            return doc_res
        docs = doc_res.get("data") or []
        if not docs:
            return {"ok": False, "error": "pedido no encontrado"}
        doc = docs[0]

        items_res = SupabaseClient(ctx).rest_select(
            "sales_document_items",
            filters={"document_id": doc["id"]},
            select=(
                "id,folio,document_id,product_id,inventory_product_id,product_folio_snapshot,"
                "product_name_snapshot,description,quantity,unit,unit_price,unit_price_ex_vat,"
                "vat_rate,vat_amount,unit_price_inc_vat,line_subtotal,tax_rate,tax_amount,"
                "line_total,weight_kg_per_unit,weight_kg_total,weight_source,metadata,created_at"
            ),
            order="created_at.asc",
            limit=500,
        )
        if not items_res.get("ok"):
            return items_res
        return {"ok": True, "data": {"pedido": doc, "items": items_res.get("data") or []}}

    def _sales_context(self, context: dict) -> dict:
        schema = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_ventas/sales_schema requerido"}
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        return {"ok": True, "data": {**context, "schema": schema, "company_id": company_id, "empresa_id": company_id}}
