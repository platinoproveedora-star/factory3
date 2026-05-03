"""Service for render_create_service - creates a web service on Render."""
from __future__ import annotations
import json
import os
import urllib.request


class RenderCreateServiceService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        for field in ("name", "repo", "owner_id"):
            if not context.get(field):
                return False, f"{field} es requerido"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        env_vars = context.get("env_vars", {})
        payload = {
            "type": "web_service",
            "name": context["name"],
            "ownerId": context["owner_id"],
            "repo": context["repo"],
            "autoDeploy": "yes",
            "serviceDetails": {
                "runtime": context.get("runtime", "python"),
                "buildCommand": context.get("build_command", "pip install -r requirements.txt"),
                "startCommand": context.get("start_command", "uvicorn factory_api:app --host 0.0.0.0 --port $PORT"),
                "plan": context.get("plan", "free"),
                "region": context.get("region", "oregon"),
                "branch": context.get("branch", "main"),
                "envVars": [{"key": k, "value": v} for k, v in env_vars.items()],
            },
        }
        try:
            result = self._request("POST", "/services", payload=payload)
            service = result.get("service", result)
            return {
                "ok": True,
                "data": {
                    "id": service.get("id"),
                    "name": service.get("name"),
                    "url": service.get("serviceDetails", {}).get("url", ""),
                    "status": service.get("suspended", "active"),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
