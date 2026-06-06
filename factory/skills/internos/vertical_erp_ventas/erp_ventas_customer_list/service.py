from __future__ import annotations
from factory.engine import SupabaseClient


class ErpVentasCustomerListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema_inventario") or context.get("schema") or "uc101_proy004"}
        result = SupabaseClient(ctx).rest_select(
            "erp_parties",
            filters={"party_type": "in.(customer,both)", "active": "eq.true"},
            select="id,folio,party_name,phone,email,address",
            order="party_name.asc",
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"customers": result.get("data", [])}}
