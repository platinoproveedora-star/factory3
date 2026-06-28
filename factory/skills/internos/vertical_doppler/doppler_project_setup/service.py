"""Crea un proyecto Doppler con ambientes estándar (dev/staging/production)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_API = "https://api.doppler.com/v3"
_DEFAULT_ENVIRONMENTS = ["dev", "staging", "production"]


class DopplerProjectSetupService:

    def ejecutar(self, context: dict) -> dict:
        token = (context.get("token") or os.getenv("DOPPLER_TOKEN", "")).strip()
        if not token:
            return {"ok": False, "error": "token requerido (o env DOPPLER_TOKEN)"}

        action = (context.get("action") or "setup").strip()

        if action == "list_projects":
            return self._list_projects(token)

        # action == "setup"
        name        = (context.get("project_name") or context.get("name") or "").strip()
        description = (context.get("description") or "").strip()
        envs        = context.get("environments") or _DEFAULT_ENVIRONMENTS

        if not name:
            return {"ok": False, "error": "project_name requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — proyecto no creado", "data": {
                "project_name": name, "environments": envs,
            }}

        # 1 — Crear proyecto
        try:
            project = self._api_post(token, "/projects", {
                "name": name, "description": description,
            })
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            # 409 = ya existe
            if e.code == 409:
                return {"ok": True, "message": f"Proyecto '{name}' ya existe en Doppler",
                        "data": {"project_name": name, "created": False}}
            return {"ok": False, "error": f"Doppler API {e.code}: {body[:300]}"}
        except Exception as e:
            return {"ok": False, "error": f"Error creando proyecto: {e}"}

        created_envs = []

        # 2 — Crear environments
        for env_name in envs:
            try:
                self._api_post(token, "/environments", {
                    "project": name,
                    "name":    env_name,
                    "slug":    env_name,
                })
                created_envs.append(env_name)
            except urllib.error.HTTPError as e:
                if e.code != 409:  # ignorar si ya existe
                    pass
            except Exception:
                pass

        return {
            "ok":      True,
            "message": f"Proyecto '{name}' creado con ambientes: {', '.join(created_envs or envs)}",
            "data": {
                "project_name":  name,
                "created":       True,
                "environments":  created_envs or envs,
                "next_step":     "Usa doppler_secret_set para cargar los secrets iniciales",
            },
        }

    def _list_projects(self, token: str) -> dict:
        try:
            resp = self._api_get(token, "/projects")
            projects = resp.get("projects") or []
        except Exception as e:
            return {"ok": False, "error": f"Error listando proyectos: {e}"}
        return {
            "ok":      True,
            "message": f"{len(projects)} proyecto(s) en Doppler",
            "data":    {"projects": [{"name": p.get("name"), "description": p.get("description")} for p in projects]},
        }

    def _api_get(self, token: str, path: str) -> dict:
        req = urllib.request.Request(
            f"{_API}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept":        "application/json",
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _api_post(self, token: str, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{_API}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "Accept":        "application/json",
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
