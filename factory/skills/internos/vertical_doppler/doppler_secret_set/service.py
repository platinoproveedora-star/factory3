"""Crea o actualiza secrets en Doppler. Nunca loguea valores — solo nombres."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_API = "https://api.doppler.com/v3"


class DopplerSecretSetService:

    def ejecutar(self, context: dict) -> dict:
        token   = (context.get("token") or os.getenv("DOPPLER_TOKEN", "")).strip()
        project = (context.get("project") or "").strip()
        config  = (context.get("config") or "production").strip()
        secrets = context.get("secrets") or {}

        if not token:
            return {"ok": False, "error": "token requerido (o env DOPPLER_TOKEN)"}
        if not project:
            return {"ok": False, "error": "project requerido"}
        if not isinstance(secrets, dict) or not secrets:
            return {"ok": False, "error": "secrets debe ser un dict no vacío {NOMBRE: valor}"}

        names = list(secrets.keys())

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — secrets no guardados", "data": {
                "project": project, "config": config,
                "secrets_names": names,  # solo nombres, nunca valores en dry_run
            }}

        try:
            self._api_post(token, "/configs/config/secrets", {
                "project": project,
                "config":  config,
                "secrets": secrets,
            })
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Doppler API {e.code}: {body[:300]}"}
        except Exception as e:
            return {"ok": False, "error": f"Error guardando secrets: {e}"}

        return {
            "ok":      True,
            "message": f"{len(names)} secret(s) guardados en {project}/{config}",
            "data": {
                "project":      project,
                "config":       config,
                "secrets_set":  names,  # solo nombres — nunca loguear valores
            },
        }

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
