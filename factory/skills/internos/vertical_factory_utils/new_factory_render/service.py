"""Creates a Render web service from a GitHub repo and waits for deploy."""
from __future__ import annotations
import json
import os
import time
import urllib.request

RENDER_TERMINAL = {"live", "deactivated", "build_failed", "update_failed", "canceled"}


class NewFactoryRenderService:

    def ejecutar(self, context: dict) -> dict:
        ok, error = self._validar(context)
        if not ok:
            return {"ok": False, "error": error}
        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": self._safe_plan(context)}

        repo = context["repo"]
        env_vars = context.get("env_vars", {})

        service = self._create_service(context, repo, env_vars)
        service_id = service.get("id", "")
        service_url = service.get("url", "")

        if context.get("wait_for_deploy", True) and service_id:
            service_url, deploy_status = self._wait(service_id, int(context.get("max_wait_seconds", 360)))
        else:
            deploy_status = "created"

        return {
            "ok": True,
            "message": f"Servicio '{context['service_name']}' desplegado",
            "data": {
                "service_id": service_id,
                "service_url": service_url,
                "deploy_status": deploy_status,
            },
        }

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        for field in ("repo", "service_name", "render_owner_id"):
            if not context.get(field):
                return False, f"{field} es requerido"
        return True, None

    def _safe_plan(self, context: dict) -> dict:
        env_vars = context.get("env_vars", {})
        return {
            "repo": context.get("repo"),
            "service_name": context.get("service_name"),
            "render_owner_id_set": bool(context.get("render_owner_id")),
            "branch": context.get("branch", "main"),
            "plan": context.get("plan", "free"),
            "region": context.get("region", "oregon"),
            "wait_for_deploy": context.get("wait_for_deploy", True),
            "env_vars": {key: bool(value) for key, value in env_vars.items()},
            "build_command": context.get("build_command", "pip install -r requirements.txt"),
            "start_command": context.get("start_command", "uvicorn factory_api:app --host 0.0.0.0 --port $PORT"),
        }

    def _create_service(self, context: dict, repo: str, env_vars: dict) -> dict:
        start_cmd = context.get("start_command", "uvicorn factory_api:app --host 0.0.0.0 --port $PORT")
        build_cmd = context.get("build_command", "pip install -r requirements.txt")
        payload = {
            "type": "web_service",
            "name": context["service_name"],
            "ownerId": context["render_owner_id"],
            "repo": f"https://github.com/{repo}",
            "autoDeploy": "yes",
            "branch": context.get("branch", "main"),
            "envVars": [{"key": k, "value": v} for k, v in env_vars.items() if v],
            "serviceDetails": {
                "env": "python",
                "plan": context.get("plan", "free"),
                "region": context.get("region", "oregon"),
                "numInstances": 1,
                "envSpecificDetails": {
                    "buildCommand": build_cmd,
                    "startCommand": start_cmd,
                },
            },
        }
        result = self._render("POST", "/services", payload)
        service = result.get("service", result)
        return {
            "id": service.get("id", ""),
            "name": service.get("name", ""),
            "url": service.get("serviceDetails", {}).get("url", ""),
        }

    def _wait(self, service_id: str, max_wait: int) -> tuple[str, str]:
        elapsed = 0
        interval = 20
        while True:
            deploys = self._render("GET", f"/services/{service_id}/deploys?limit=1")
            if deploys:
                deploy = deploys[0].get("deploy", deploys[0])
                status = deploy.get("status", "")
                if status in RENDER_TERMINAL:
                    if status != "live":
                        raise RuntimeError(f"Deploy termino con estado: {status}")
                    svc = self._render("GET", f"/services/{service_id}")
                    svc = svc.get("service", svc)
                    url = svc.get("serviceDetails", {}).get("url", "")
                    if not url:
                        url = f"https://{service_id}.onrender.com"
                    return url, status
            if elapsed >= max_wait:
                raise TimeoutError(f"Deploy no termino en {max_wait}s")
            time.sleep(interval)
            elapsed += interval

    def _render(self, method: str, path: str, payload: dict | None = None) -> dict:
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}
