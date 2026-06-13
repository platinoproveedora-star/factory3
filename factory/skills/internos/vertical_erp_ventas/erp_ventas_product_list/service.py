from __future__ import annotations
from factory.engine import SupabaseClient


class ErpVentasProductListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._inventory_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        result = SupabaseClient(ctx).rest_select(
            "erp_products",
            filters={"active": "eq.true"},
            select="id,folio,product_name,sku,unit,category,min_stock,weight_kg,weight_unit,weight_notes",
            order="product_name.asc",
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"products": result.get("data", [])}}

    def _inventory_context(self, context: dict) -> dict:
        schema = str(context.get("schema_inventario") or context.get("inventory_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_inventario/inventory_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
