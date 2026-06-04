from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request


class RenderNextjsServiceDeployService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        for field in ("service_name", "repo", "root_dir"):
            if not str(context.get(field) or "").strip():
                return {"ok": False, "error": f"{field} requerido"}

        ctx = {
            "service_name": str(context["service_name"]).strip(),
            "repo": str(context["repo"]).strip(),
            "root_dir": str(context["root_dir"]).strip().replace("\\", "/").strip("/"),
            "branch": str(context.get("branch") or "main").strip(),
            "owner_id": str(context.get("owner_id") or os.getenv("RENDER_OWNER_ID") or "").strip(),
            "build_command": str(context.get("build_command") or "npm install && npm run build").strip(),
            "start_command": str(context.get("start_command") or "npm start").strip(),
            "plan": str(context.get("plan") or "free").strip(),
            "region": str(context.get("region") or "oregon").strip(),
            "env_vars": context.get("env_vars") if isinstance(context.get("env_vars"), dict) else {},
            "wait": bool(context.get("wait", True)),
            "max_wait_seconds": int(context.get("max_wait_seconds") or 600),
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"plan": ctx}}

        try:
            service = self._find_service(ctx["service_name"])
            created = False
            if not service:
                if not ctx["owner_id"]:
                    return {"ok": False, "error": "owner_id o RENDER_OWNER_ID requerido para crear servicio"}
                service = self._create_service(ctx)
                created = True
            service_id = service.get("id")
            if not service_id:
                return {"ok": False, "error": "Render no devolvio service_id"}

            env_count = 0
            if ctx["env_vars"]:
                env_count = self._set_env_vars(service_id, ctx["env_vars"])
            deploy = self._trigger_deploy(service_id)
            deploy_status = self._wait_deploy(service_id, deploy.get("id"), ctx["max_wait_seconds"]) if ctx["wait"] else deploy
            service_detail = self._get_service(service_id)
            return {
                "ok": True,
                "data": {
                    "service_id": service_id,
                    "service_name": service_detail.get("name") or ctx["service_name"],
                    "url": (service_detail.get("serviceDetails") or {}).get("url", ""),
                    "created": created,
                    "env_vars_count": env_count,
                    "deploy": deploy_status,
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _create_service(self, ctx: dict) -> dict:
        payload = {
            "type": "web_service",
            "name": ctx["service_name"],
            "ownerId": ctx["owner_id"],
            "repo": ctx["repo"],
            "branch": ctx["branch"],
            "autoDeploy": "yes",
            "rootDir": ctx["root_dir"],
            "serviceDetails": {
                "env": "node",
                "plan": ctx["plan"],
                "region": ctx["region"],
                "envSpecificDetails": {
                    "buildCommand": ctx["build_command"],
                    "startCommand": ctx["start_command"],
                },
                "envVars": [{"key": k, "value": str(v)} for k, v in ctx["env_vars"].items()],
            },
        }
        result = self._request("POST", "/services", payload)
        return result.get("service", result)

    def _find_service(self, name: str) -> dict | None:
        services = self._request("GET", f"/services?name={urllib.parse.quote(name)}&limit=20")
        for item in services or []:
            service = item.get("service", item)
            if service.get("name") == name:
                return service
        return None

    def _get_service(self, service_id: str) -> dict:
        return self._request("GET", f"/services/{service_id}")

    def _set_env_vars(self, service_id: str, env_vars: dict) -> int:
        existing = {}
        try:
            rows = self._request("GET", f"/services/{service_id}/env-vars")
            existing = {row["envVar"]["key"]: row["envVar"]["value"] for row in rows if row.get("envVar")}
        except Exception:
            existing = {}
        existing.update({k: str(v) for k, v in env_vars.items()})
        payload = [{"key": k, "value": v} for k, v in existing.items()]
        self._request("PUT", f"/services/{service_id}/env-vars", payload)
        return len(payload)

    def _trigger_deploy(self, service_id: str) -> dict:
        result = self._request("POST", f"/services/{service_id}/deploys", {"clearCache": "clear"})
        return result.get("deploy", result)

    def _wait_deploy(self, service_id: str, deploy_id: str | None, max_wait: int) -> dict:
        started = time.time()
        while True:
            deploys = self._request("GET", f"/services/{service_id}/deploys?limit=5")
            deploy = None
            for row in deploys or []:
                candidate = row.get("deploy", row)
                if not deploy_id or candidate.get("id") == deploy_id:
                    deploy = candidate
                    break
            if not deploy:
                return {"id": deploy_id, "status": "unknown"}
            status = str(deploy.get("status") or "")
            if status in {"live", "build_failed", "update_failed", "canceled", "deactivated"}:
                return {
                    "id": deploy.get("id"),
                    "status": status,
                    "created_at": deploy.get("createdAt", ""),
                    "updated_at": deploy.get("updatedAt", ""),
                }
            if time.time() - started > max_wait:
                return {"id": deploy.get("id"), "status": status, "timeout": True}
            time.sleep(10)

    def _request(self, method: str, path: str, payload=None):
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
