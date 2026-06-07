from __future__ import annotations
from factory.engine import SupabaseClient


class ErpVentasCustomerListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._inventory_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        result = SupabaseClient(ctx).rest_select(
            "erp_parties",
            filters={"party_type": "in.(customer,both)", "active": "eq.true"},
            select="id,folio,party_name,phone,email,address",
            order="party_name.asc",
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"customers": result.get("data", [])}}

    def _inventory_context(self, context: dict) -> dict:
        schema = str(context.get("schema_inventario") or context.get("inventory_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_inventario/inventory_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
