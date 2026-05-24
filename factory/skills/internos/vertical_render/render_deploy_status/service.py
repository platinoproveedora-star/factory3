"""Service for render_deploy_status - polls a deploy until live or failed."""
from __future__ import annotations
import json
import os
import time
import urllib.request


TERMINAL_STATUSES = {"live", "deactivated", "build_failed", "update_failed", "canceled"}


class RenderDeployStatusService:

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
        deploy_id = context.get("deploy_id")
        wait = context.get("wait", True)
        max_wait = int(context.get("max_wait_seconds", 300))
        interval = int(context.get("poll_interval_seconds", 15))
        try:
            if deploy_id:
                return self._poll_deploy(service_id, deploy_id, wait, max_wait, interval)
            return self._poll_latest_deploy(service_id, wait, max_wait, interval)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _poll_deploy(self, service_id: str, deploy_id: str, wait: bool, max_wait: int, interval: int) -> dict:
        elapsed = 0
        while True:
            deploys = self._request("GET", f"/services/{service_id}/deploys?limit=5")
            deploy = next((d.get("deploy", d) for d in deploys if d.get("deploy", d).get("id") == deploy_id), None)
            if not deploy:
                return {"ok": False, "error": f"deploy_id '{deploy_id}' no encontrado"}
            status = deploy.get("status", "")
            if not wait or status in TERMINAL_STATUSES:
                return self._format_result(service_id, deploy, elapsed)
            if elapsed >= max_wait:
                return {"ok": False, "error": f"Timeout: deploy no terminó en {max_wait}s", "status": status}
            time.sleep(interval)
            elapsed += interval

    def _poll_latest_deploy(self, service_id: str, wait: bool, max_wait: int, interval: int) -> dict:
        elapsed = 0
        while True:
            deploys = self._request("GET", f"/services/{service_id}/deploys?limit=1")
            if not deploys:
                return {"ok": False, "error": "No hay deploys para este servicio"}
            deploy = deploys[0].get("deploy", deploys[0])
            status = deploy.get("status", "")
            if not wait or status in TERMINAL_STATUSES:
                return self._format_result(service_id, deploy, elapsed)
            if elapsed >= max_wait:
                return {"ok": False, "error": f"Timeout: deploy no terminó en {max_wait}s", "status": status}
            time.sleep(interval)
            elapsed += interval

    def _format_result(self, service_id: str, deploy: dict, elapsed: int) -> dict:
        status = deploy.get("status", "")
        live = status == "live"
        return {
            "ok": live,
            "data": {
                "deploy_id": deploy.get("id"),
                "status": status,
                "live": live,
                "elapsed_seconds": elapsed,
                "created_at": deploy.get("createdAt", ""),
                "updated_at": deploy.get("updatedAt", ""),
            },
            "message": "Deploy live" if live else f"Deploy terminó con estado: {status}",
        }

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
