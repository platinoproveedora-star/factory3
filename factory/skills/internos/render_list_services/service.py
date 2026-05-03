"""Service for render_list_services - lists all Render services."""
from __future__ import annotations
import json
import os
import urllib.request


class RenderListServicesService:

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
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        limit = min(context.get("limit", 20), 100)
        service_type = context.get("type", "")
        path = f"/services?limit={limit}"
        if service_type:
            path += f"&type={service_type}"
        try:
            result = self._request("GET", path)
            services = []
            for item in result:
                svc = item.get("service", item)
                details = svc.get("serviceDetails", {})
                services.append({
                    "id": svc.get("id"),
                    "name": svc.get("name"),
                    "url": details.get("url", ""),
                    "suspended": svc.get("suspended", "not_suspended"),
                    "type": svc.get("type", ""),
                })
            return {"ok": True, "data": {"services": services, "count": len(services)}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, method: str, path: str) -> list:
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}", method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
