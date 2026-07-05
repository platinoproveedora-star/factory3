from __future__ import annotations

import re
from urllib.parse import urlparse

from factory.engine import SupabaseClient


MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
STATUSES = {"draft", "beta", "live", "deprecated"}


class Apps4AllModuleUrlActivateService:
    def ejecutar(self, context: dict) -> dict:
        module_code = str(context.get("module_code") or context.get("modulo_code") or "").strip()
        app_url = str(context.get("app_url") or context.get("url") or "").strip().rstrip("/")
        status = str(context.get("marketplace_status") or context.get("status") or "live").strip()
        if not MODULE_RE.match(module_code):
            return {"ok": False, "error": "module_code invalido"}
        if not self._valid_url(app_url):
            return {"ok": False, "error": "app_url https requerido"}
        if status not in STATUSES:
            return {"ok": False, "error": "status debe ser draft|beta|live|deprecated"}

        row = {
            "code": module_code,
            "activo": bool(context.get("active", context.get("activo", True))),
            "marketplace_status": status,
            "app_url": app_url,
            "prod_url": context.get("prod_url") or app_url,
            "demo_url": context.get("demo_url") or app_url,
            "metadata": context.get("metadata") or {},
        }
        if context.get("title") or context.get("nombre"):
            row["nombre"] = context.get("title") or context.get("nombre")
        if context.get("description"):
            row["description"] = context.get("description")
        if context.get("category"):
            row["category"] = context.get("category")
        if context.get("pricing_json") is not None:
            row["pricing_json"] = context.get("pricing_json")
        if context.get("tags") is not None:
            row["tags"] = context.get("tags")

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"module": row}}

        result = SupabaseClient({"schema": "platform"}).rest_upsert("modulos", row, "code")
        if not result.get("ok"):
            return result
        return {"ok": True, "message": "module url activated", "data": {"module": (result.get("data") or [row])[0]}}

    def _valid_url(self, value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
