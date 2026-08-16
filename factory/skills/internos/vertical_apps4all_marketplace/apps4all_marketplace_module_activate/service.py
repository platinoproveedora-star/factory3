from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class Apps4AllMarketplaceModuleActivateService:
    """platform.access_grants vive en el proyecto Supabase de la plataforma
    (PLATFORM_SUPABASE_*), no en el proyecto operativo de ninguna empresa.
    """

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

        url = (context.get("platform_supabase_url") or os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = context.get("platform_supabase_service_role_key") or os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        req = urllib.request.Request(
            f"{url}/rest/v1/access_grants?on_conflict=user_id,company_id,modulo_code",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Content-Profile": "platform",
                "Prefer": "resolution=merge-duplicates,return=representation",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"}
        return {"ok": True, "message": "module activated", "data": {"grant": (data or [row])[0]}}
