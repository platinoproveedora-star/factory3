"""Service for meta_revoke_connection - revokes Meta permissions."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class MetaRevokeConnectionService:

    def ejecutar(self, context: dict) -> dict:
        access_token = self._get_text(context, "access_token") or os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN")
        graph_version = self._graph_version(context)
        if not access_token:
            return {"ok": False, "error": "access_token es requerido en context, META_ACCESS_TOKEN o IG_ACCESS_TOKEN"}
        if context.get("dry_run", False):
            return {
                "ok": True,
                "message": "dry_run",
                "data": {"graph_version": graph_version, "endpoint": f"/{graph_version}/me/permissions", "method": "DELETE"},
            }

        try:
            data = urllib.parse.urlencode({"access_token": access_token}).encode("utf-8")
            url = f"https://graph.facebook.com/{graph_version}/me/permissions"
            req = urllib.request.Request(
                url,
                data=data,
                headers={"content-type": "application/x-www-form-urlencoded"},
                method="DELETE",
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            return {"ok": bool(result.get("success", True)), "data": result}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": self._http_error_message(exc)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _http_error_message(self, exc: urllib.error.HTTPError) -> str:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            return body.get("error", {}).get("message", str(exc))
        except Exception:
            return str(exc)

    def _get_text(self, context: dict, key: str) -> str | None:
        value = context.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _graph_version(self, context: dict) -> str:
        return self._get_text(context, "graph_version") or os.getenv("META_GRAPH_API_VERSION") or os.getenv("IG_GRAPH_API_VERSION") or "v24.0"
