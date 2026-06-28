"""Verifica el estado de salud de un proyecto Supabase via Management API."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_API            = "https://api.supabase.com/v1"
_HEALTHY_STATUS = "ACTIVE_HEALTHY"


class SupabaseProjectStatusCheckService:

    def ejecutar(self, context: dict) -> dict:
        access_token = (context.get("access_token") or
                        os.getenv("SUPABASE_ACCESS_TOKEN", "")).strip()
        project_ref  = (context.get("project_ref") or
                        os.getenv("SUPABASE_PROJECT_REF", "")).strip()

        if not access_token:
            return {"ok": False, "error": "access_token requerido (o env SUPABASE_ACCESS_TOKEN)"}
        if not project_ref:
            return {"ok": False, "error": "project_ref requerido"}

        try:
            health = self._api_get(access_token, f"/projects/{project_ref}/health")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase API {e.code}: {body[:300]}"}
        except Exception as e:
            return {"ok": False, "error": f"Error consultando salud: {e}"}

        if isinstance(health, list):
            statuses   = {h.get("status") for h in health}
            is_healthy = statuses == {_HEALTHY_STATUS}
            status     = _HEALTHY_STATUS if is_healthy else next(iter(statuses), "UNKNOWN")
            services   = [{"name": h.get("name"), "status": h.get("status")} for h in health]
        elif isinstance(health, dict):
            status     = health.get("status", "UNKNOWN")
            is_healthy = status == _HEALTHY_STATUS
            services   = [{"name": "project", "status": status}]
        else:
            return {"ok": False, "error": f"Respuesta inesperada: {str(health)[:200]}"}

        url = f"https://{project_ref}.supabase.co" if is_healthy else None

        return {
            "ok":      True,
            "message": f"Proyecto {project_ref}: {status}",
            "data": {
                "project_ref": project_ref,
                "status":      status,
                "is_healthy":  is_healthy,
                "url":         url,
                "services":    services,
            },
        }

    def _api_get(self, token: str, path: str) -> dict | list:
        req = urllib.request.Request(
            f"{_API}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
