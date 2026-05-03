"""Service for render_get_service - gets info about a Render service."""
from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request


class RenderGetServiceService:

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
        if not context.get("service_id") and not context.get("name"):
            return False, "service_id o name es requerido"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        try:
            if context.get("service_id"):
                result = self._request("GET", f"/services/{context['service_id']}")
                service = result
            else:
                services = self._request("GET", f"/services?name={urllib.parse.quote(context['name'])}&limit=1")
                if not services:
                    return {"ok": False, "error": f"Servicio '{context['name']}' no encontrado"}
                service = services[0].get("service", services[0])
            details = service.get("serviceDetails", {})
            return {
                "ok": True,
                "data": {
                    "id": service.get("id"),
                    "name": service.get("name"),
                    "url": details.get("url", ""),
                    "deploy_status": details.get("lastSuccessfulRunAt", "unknown"),
                    "suspended": service.get("suspended", "not_suspended"),
                    "created_at": service.get("createdAt", ""),
                    "updated_at": service.get("updatedAt", ""),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, method: str, path: str) -> dict:
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}", method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
