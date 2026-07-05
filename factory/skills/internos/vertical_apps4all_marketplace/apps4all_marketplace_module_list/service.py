from __future__ import annotations

from factory.engine import SupabaseClient


class Apps4AllMarketplaceModuleListService:
    def ejecutar(self, context: dict) -> dict:
        filters = {}
        if context.get("status"):
            filters["marketplace_status"] = str(context["status"])
        if context.get("active") is not None:
            filters["activo"] = str(bool(context["active"])).lower()
        select = "code,nombre,description,category,marketplace_status,activo,app_url,demo_url,prod_url,icon,sort_order,default_plan_code,pricing_json,tags,metadata"
        result = SupabaseClient({"schema": "platform"}).rest_select("modulos", filters=filters, select=select, limit=int(context.get("limit") or 500), order="sort_order.asc,code.asc")
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"modules": result.get("data") or []}}
