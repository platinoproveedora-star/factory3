from __future__ import annotations
from factory.engine import SupabaseClient


class ErpVentasProductListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema_inventario") or context.get("schema") or "uc101_proy004"}
        result = SupabaseClient(ctx).rest_select(
            "erp_products",
            filters={"active": "eq.true"},
            select="id,folio,product_name,sku,unit,category,min_stock",
            order="product_name.asc",
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"products": result.get("data", [])}}
