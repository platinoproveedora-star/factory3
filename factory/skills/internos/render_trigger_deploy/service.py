"""Service for render_trigger_deploy - triggers a manual deploy on Render."""
from __future__ import annotations
import json
import os
import urllib.request


class RenderTriggerDeployService:

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
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        service_id = context["service_id"]
        payload = {"clearCache": "do_not_clear"}
        if context.get("clear_cache", False):
            payload["clearCache"] = "clear"
        try:
            result = self._request("POST", f"/services/{service_id}/deploys", payload=payload)
            deploy = result.get("deploy", result)
            return {
                "ok": True,
                "data": {
                    "deploy_id": deploy.get("id"),
                    "status": deploy.get("status", "created"),
                    "created_at": deploy.get("createdAt", ""),
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
