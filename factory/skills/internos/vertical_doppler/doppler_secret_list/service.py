"""Lista secrets de un proyecto/config Doppler. Valores solo si include_values=True."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_API = "https://api.doppler.com/v3"


class DopplerSecretListService:

    def ejecutar(self, context: dict) -> dict:
        token          = (context.get("token") or os.getenv("DOPPLER_TOKEN", "")).strip()
        project        = (context.get("project") or "").strip()
        config         = (context.get("config") or "production").strip()
        include_values = context.get("include_values", False)

        if not token:
            return {"ok": False, "error": "token requerido (o env DOPPLER_TOKEN)"}
        if not project:
            return {"ok": False, "error": "project requerido"}

        try:
            qs   = f"?project={project}&config={config}"
            resp = self._api_get(token, f"/configs/config/secrets{qs}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Doppler API {e.code}: {body[:300]}"}
        except Exception as e:
            return {"ok": False, "error": f"Error listando secrets: {e}"}

        raw     = resp.get("secrets") or {}
        names   = list(raw.keys())

        if include_values:
            secrets_out = {k: v.get("computed", "") for k, v in raw.items()}
        else:
            secrets_out = {k: "***" for k in names}

        return {
            "ok":      True,
            "message": f"{len(names)} secret(s) en {project}/{config}",
            "data": {
                "project":        project,
                "config":         config,
                "count":          len(names),
                "secrets":        secrets_out,
                "include_values": include_values,
            },
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
