"""Service for render_set_env_vars - sets env vars on a Render service."""
from __future__ import annotations
import json
import os
import urllib.request


class RenderSetEnvVarsService:

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
        if not context.get("service_id"):
            return False, "service_id es requerido"
        if not context.get("env_vars") or not isinstance(context["env_vars"], dict):
            return False, "env_vars es requerido y debe ser un diccionario {KEY: VALUE}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        service_id = context["service_id"]
        new_vars = context["env_vars"]
        merge = context.get("merge", True)
        try:
            if merge:
                existing = self._get_existing_vars(service_id)
                existing.update(new_vars)
                final_vars = existing
            else:
                final_vars = new_vars
            payload = [{"key": k, "value": v} for k, v in final_vars.items()]
            self._request("PUT", f"/services/{service_id}/env-vars", payload=payload)
            return {"ok": True, "message": f"{len(final_vars)} variables configuradas", "data": {"count": len(final_vars)}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _get_existing_vars(self, service_id: str) -> dict:
        try:
            result = self._request("GET", f"/services/{service_id}/env-vars")
            return {item["envVar"]["key"]: item["envVar"]["value"] for item in result if "envVar" in item}
        except Exception:
            return {}

    def _request(self, method: str, path: str, payload=None) -> dict:
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
