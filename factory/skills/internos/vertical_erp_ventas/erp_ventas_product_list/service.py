from __future__ import annotations
from factory.engine import SupabaseClient


class ErpVentasProductListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": "uc101_proy002"}
        result = SupabaseClient(ctx).rest_select(
            "sales_products",
            filters={"active": "eq.true"},
            select="id,folio,product_name,sku,unit,unit_price,category",
            order="product_name.asc",
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"products": result.get("data", [])}}
