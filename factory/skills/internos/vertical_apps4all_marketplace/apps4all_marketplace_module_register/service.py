from __future__ import annotations

import re

from factory.engine import SupabaseClient


CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
STATUSES = {"draft", "beta", "live", "deprecated"}


class Apps4AllMarketplaceModuleRegisterService:
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

        db = SupabaseClient({"schema": "platform"})
        result = db.rest_upsert("modulos", row, "code")
        if not result.get("ok"):
            return result
        return {"ok": True, "message": "module registered", "data": {"module": (result.get("data") or [row])[0]}}
