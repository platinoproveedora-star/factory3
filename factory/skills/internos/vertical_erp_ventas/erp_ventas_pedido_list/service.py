from __future__ import annotations

from factory.engine import SupabaseClient


class ErpVentasPedidoListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._sales_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        limit = min(max(int(context.get("limit") or 50), 1), 500)
        filters: dict = {"document_type": "eq.pedido"}
        if context.get("customer_id"):
            filters["customer_id"] = f"eq.{context['customer_id']}"
        if context.get("status"):
            filters["status"] = f"eq.{context['status']}"
        if context.get("city"):
            filters["city"] = f"eq.{context['city']}"
        if context.get("city_quadrant"):
            filters["city_quadrant"] = f"eq.{context['city_quadrant']}"

        result = SupabaseClient(ctx).rest_select(
            "sales_documents",
            filters=filters,
            select="id,folio,external_folio,customer_id,customer_name_snapshot,status,document_date,due_date,delivery_address,payment_method,city,city_quadrant,total_weight_kg,subtotal,tax_total,total,balance_total,notes,created_at",
            order="created_at.desc",
            limit=limit,
        )
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        date_from = str(context.get("date_from") or "").strip()
        date_to = str(context.get("date_to") or "").strip()
        if date_from:
            rows = [row for row in rows if str(row.get("document_date") or "") >= date_from]
        if date_to:
            rows = [row for row in rows if str(row.get("document_date") or "") <= date_to]
        return {"ok": True, "data": {"pedidos": rows}}

    def _sales_context(self, context: dict) -> dict:
        schema = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_ventas/sales_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
