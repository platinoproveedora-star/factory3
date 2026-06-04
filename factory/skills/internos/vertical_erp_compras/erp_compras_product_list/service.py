from __future__ import annotations

from factory.engine import SupabaseClient


class ErpComprasProductListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        result = SupabaseClient(ctx).rest_select("erp_products", filters={"active": "eq.true"}, select="*", order="product_name.asc", limit=1000)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"products": result.get("data") or []}}
