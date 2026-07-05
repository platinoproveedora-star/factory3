from __future__ import annotations

from factory.engine import SupabaseClient


class Apps4AllMarketplaceModuleActivateService:
    def ejecutar(self, context: dict) -> dict:
        user_id = str(context.get("user_id") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        module_code = str(context.get("module_code") or context.get("modulo_code") or "").strip()
        if not user_id:
            return {"ok": False, "error": "user_id requerido"}
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not module_code:
            return {"ok": False, "error": "module_code requerido"}

        row = {
            "user_id": user_id,
            "company_id": company_id,
            "modulo_code": module_code,
            "role": context.get("role") or "owner",
            "status": context.get("status") or "manual",
            "plan_code": context.get("plan_code") or f"{module_code}_manual",
            "subscription_status": context.get("subscription_status") or "manual",
            "metadata": context.get("metadata") or {},
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"grant": row}}
        result = SupabaseClient({"schema": "platform"}).rest_upsert("access_grants", row, "user_id,company_id,modulo_code")
        if not result.get("ok"):
            return result
        return {"ok": True, "message": "module activated", "data": {"grant": (result.get("data") or [row])[0]}}
