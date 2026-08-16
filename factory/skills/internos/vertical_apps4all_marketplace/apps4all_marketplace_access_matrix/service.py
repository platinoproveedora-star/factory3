from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class Apps4AllMarketplaceAccessMatrixService:
    """platform.access_grants vive en el proyecto Supabase de la plataforma
    (PLATFORM_SUPABASE_*), no en el proyecto operativo de ninguna empresa.
    """

    def ejecutar(self, context: dict) -> dict:
        url = (context.get("platform_supabase_url") or os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = context.get("platform_supabase_service_role_key") or os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        params = {
            "select": "id,user_id,company_id,modulo_code,role,status,plan_code,subscription_status,current_period_end,metadata",
            "order": "company_id.asc,modulo_code.asc",
            "limit": str(int(context.get("limit") or 1000)),
        }
        if context.get("company_id") or context.get("empresa_id"):
            params["company_id"] = f"eq.{context.get('company_id') or context.get('empresa_id')}"
        if context.get("module_code") or context.get("modulo_code"):
            params["modulo_code"] = f"eq.{context.get('module_code') or context.get('modulo_code')}"

        req = urllib.request.Request(
            f"{url}/rest/v1/access_grants?{urllib.parse.urlencode(params)}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept-Profile": "platform",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"}
        grants = data or []
        return {"ok": True, "data": {"grants": grants, "count": len(grants)}}
