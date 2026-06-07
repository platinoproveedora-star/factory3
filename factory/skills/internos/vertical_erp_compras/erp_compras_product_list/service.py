from __future__ import annotations

from factory.engine import SupabaseClient


class ErpComprasProductListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._schema_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        result = SupabaseClient(ctx).rest_select("erp_products", filters={"active": "eq.true"}, select="*", order="product_name.asc", limit=1000)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"products": result.get("data") or []}}

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or context.get("inventory_schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema/supabase_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
