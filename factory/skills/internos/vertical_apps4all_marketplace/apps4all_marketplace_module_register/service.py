from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
STATUSES = {"draft", "beta", "live", "deprecated"}


class Apps4AllMarketplaceModuleRegisterService:
    """platform.modulos vive en el proyecto Supabase de la plataforma
    (PLATFORM_SUPABASE_*), no en el proyecto operativo de ninguna empresa.
    """

    def ejecutar(self, context: dict) -> dict:
        module_code = str(context.get("module_code") or context.get("modulo_code") or "").strip()
        title = str(context.get("title") or context.get("nombre") or module_code).strip()
        status = str(context.get("marketplace_status") or context.get("status") or "draft").strip()
        if not CODE_RE.match(module_code):
            return {"ok": False, "error": "module_code invalido"}
        if status not in STATUSES:
            return {"ok": False, "error": "status debe ser draft|beta|live|deprecated"}

        row = {
            "code": module_code,
            "nombre": title,
            "activo": bool(context.get("active", context.get("activo", True))),
            "description": context.get("description"),
            "category": context.get("category"),
            "marketplace_status": status,
            "app_url": context.get("app_url") or context.get("prod_url"),
            "demo_url": context.get("demo_url"),
            "prod_url": context.get("prod_url") or context.get("app_url"),
            "icon": context.get("icon") or "layout-dashboard",
            "sort_order": int(context.get("sort_order") or 100),
            "default_plan_code": context.get("default_plan_code") or f"{module_code}_manual",
            "pricing_json": context.get("pricing_json") or {},
            "tags": context.get("tags") or [],
            "metadata": context.get("metadata") or {},
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"module": row}}

        url = (context.get("platform_supabase_url") or os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = context.get("platform_supabase_service_role_key") or os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        req = urllib.request.Request(
            f"{url}/rest/v1/modulos?on_conflict=code",
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
        return {"ok": True, "message": "module registered", "data": {"module": (data or [row])[0]}}
