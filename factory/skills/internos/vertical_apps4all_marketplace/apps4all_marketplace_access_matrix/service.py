from __future__ import annotations

from factory.engine import SupabaseClient


class Apps4AllMarketplaceAccessMatrixService:
    def ejecutar(self, context: dict) -> dict:
        filters = {}
        if context.get("company_id") or context.get("empresa_id"):
            filters["company_id"] = str(context.get("company_id") or context.get("empresa_id"))
        if context.get("module_code") or context.get("modulo_code"):
            filters["modulo_code"] = str(context.get("module_code") or context.get("modulo_code"))
        select = "id,user_id,company_id,modulo_code,role,status,plan_code,subscription_status,current_period_end,metadata"
        result = SupabaseClient({"schema": "platform"}).rest_select("access_grants", filters=filters, select=select, limit=int(context.get("limit") or 1000), order="company_id.asc,modulo_code.asc")
        if not result.get("ok"):
            return result
        grants = result.get("data") or []
        return {"ok": True, "data": {"grants": grants, "count": len(grants)}}
