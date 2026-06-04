from __future__ import annotations

from factory.engine import SupabaseClient


class ErpComprasSupplierListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        result = SupabaseClient(ctx).rest_select("erp_parties", filters={"active": "eq.true"}, select="*", order="party_name.asc", limit=1000)
        if not result.get("ok"):
            return result
        suppliers = [
            row for row in result.get("data") or []
            if row.get("party_type") in {"supplier", "both"}
        ]
        return {"ok": True, "data": {"suppliers": suppliers}}
