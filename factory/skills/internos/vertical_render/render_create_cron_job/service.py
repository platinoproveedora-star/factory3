from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class RenderCreateCronJobService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        required = ["name", "repo", "schedule", "command"]
        missing = [field for field in required if not str(context.get(field) or "").strip()]
        if missing:
            return {"ok": False, "error": f"campos requeridos: {', '.join(missing)}"}

        ctx = {
            "name": str(context["name"]).strip(),
            "repo": str(context["repo"]).strip(),
            "schedule": str(context["schedule"]).strip(),
            "command": str(context["command"]).strip(),
            "owner_id": str(context.get("owner_id") or os.getenv("RENDER_OWNER_ID") or "").strip(),
            "branch": str(context.get("branch") or "main").strip(),
            "env": str(context.get("env") or "docker").strip(),
            "build_command": str(context.get("build_command") or "pip install -r requirements.txt").strip(),
            "plan": str(context.get("plan") or "starter").strip(),
            "region": str(context.get("region") or "oregon").strip(),
            "env_vars": context.get("env_vars") if isinstance(context.get("env_vars"), dict) else {},
        }
        if not ctx["owner_id"]:
            return {"ok": False, "error": "owner_id o RENDER_OWNER_ID requerido"}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"plan": ctx}}

        try:
            existing = self._find_service(ctx["name"])
            if existing:
                service_id = existing.get("id")
                updated = self._update_cron_job(service_id, ctx)
                self._set_env_vars(service_id, ctx["env_vars"])
                service = self._get_service(service_id)
                return {"ok": True, "data": self._format(service, updated=True, created=False)}
            created = self._create_cron_job(ctx)
            service = created.get("service", created)
            service_id = service.get("id")
            if service_id and ctx["env_vars"]:
                self._set_env_vars(service_id, ctx["env_vars"])
                service = self._get_service(service_id)
            return {"ok": True, "data": self._format(service, updated=False, created=True)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _create_cron_job(self, ctx: dict) -> dict:
        payload = {
            "type": "cron_job",
            "name": ctx["name"],
            "ownerId": ctx["owner_id"],
            "repo": ctx["repo"],
            "branch": ctx["branch"],
            "autoDeploy": "yes",
            "serviceDetails": {
                "env": ctx["env"],
                "plan": ctx["plan"],
                "region": ctx["region"],
                "schedule": ctx["schedule"],
                "envSpecificDetails": {
                    "buildCommand": ctx["build_command"],
                    "startCommand": ctx["command"],
                },
                "envVars": [{"key": key, "value": str(value)} for key, value in ctx["env_vars"].items()],
            },
        }
        return self._request("POST", "/services", payload)

    def _update_cron_job(self, service_id: str, ctx: dict) -> dict:
        payload = {
            "repo": ctx["repo"],
            "branch": ctx["branch"],
            "serviceDetails": {
                "env": ctx["env"],
                "schedule": ctx["schedule"],
                "envSpecificDetails": {
                    "buildCommand": ctx["build_command"],
                    "startCommand": ctx["command"],
                },
            },
        }
        result = self._request("PATCH", f"/services/{service_id}", payload)
        return result.get("service", result)

    def _find_service(self, name: str) -> dict | None:
        rows = self._request("GET", f"/services?name={urllib.parse.quote(name)}&limit=20")
        for row in rows or []:
            service = row.get("service", row)
            if service.get("name") == name:
                return service
        return None

    def _get_service(self, service_id: str) -> dict:
        return self._request("GET", f"/services/{service_id}")

    def _set_env_vars(self, service_id: str, env_vars: dict) -> None:
        if not env_vars:
            return
        existing = {}
        try:
            rows = self._request("GET", f"/services/{service_id}/env-vars")
            existing = {row["envVar"]["key"]: row["envVar"]["value"] for row in rows if row.get("envVar")}
        except Exception:
            existing = {}
        existing.update({key: str(value) for key, value in env_vars.items()})
        payload = [{"key": key, "value": value} for key, value in existing.items()]
        self._request("PUT", f"/services/{service_id}/env-vars", payload)

    def _format(self, service: dict, updated: bool, created: bool) -> dict:
        details = service.get("serviceDetails") or {}
        return {
            "service_id": service.get("id"),
            "name": service.get("name"),
            "type": service.get("type"),
            "schedule": details.get("schedule"),
            "created": created,
            "updated": updated,
        }

    def _request(self, method: str, path: str, payload=None):
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
