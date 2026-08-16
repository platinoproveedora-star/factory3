from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class Apps4AllMarketplaceModuleListService:
    """platform.modulos vive en el proyecto Supabase de la plataforma
    (PLATFORM_SUPABASE_*), no en el proyecto operativo de ninguna empresa.
    """

    def ejecutar(self, context: dict) -> dict:
        url = (context.get("platform_supabase_url") or os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = context.get("platform_supabase_service_role_key") or os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        params = {
            "select": "code,nombre,description,category,marketplace_status,activo,app_url,demo_url,prod_url,icon,sort_order,default_plan_code,pricing_json,tags,metadata",
            "order": "sort_order.asc,code.asc",
            "limit": str(int(context.get("limit") or 500)),
        }
        if context.get("status"):
            params["marketplace_status"] = f"eq.{context['status']}"
        if context.get("active") is not None:
            params["activo"] = f"eq.{str(bool(context['active'])).lower()}"

        req = urllib.request.Request(
            f"{url}/rest/v1/modulos?{urllib.parse.urlencode(params)}",
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
        return {"ok": True, "data": {"modules": data or []}}
