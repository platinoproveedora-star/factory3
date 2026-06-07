from __future__ import annotations

from factory.engine import SupabaseClient


class ErpComprasSupplierListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._schema_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        result = SupabaseClient(ctx).rest_select("erp_parties", filters={"active": "eq.true"}, select="*", order="party_name.asc", limit=1000)
        if not result.get("ok"):
            return result
        suppliers = [
            row for row in result.get("data") or []
            if row.get("party_type") in {"supplier", "both"}
        ]
        return {"ok": True, "data": {"suppliers": suppliers}}

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or context.get("inventory_schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema/supabase_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
