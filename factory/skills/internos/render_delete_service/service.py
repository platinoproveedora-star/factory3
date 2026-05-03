"""Service for render_delete_service - deletes a Render service."""
from __future__ import annotations
import json
import os
import urllib.request


class RenderDeleteServiceService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run: no se elimino nada", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        if not context.get("service_id"):
            return False, "service_id es requerido"
        if context.get("confirm") is not True:
            return False, "confirm: true es requerido para eliminar un servicio"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        service_id = context["service_id"]
        try:
            self._request("DELETE", f"/services/{service_id}")
            return {"ok": True, "message": f"Servicio '{service_id}' eliminado"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, method: str, path: str) -> None:
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}", method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read()
