"""Service for meta_debug_token - calls Meta Graph API /debug_token."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class MetaDebugTokenService:

    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", False)
        valido, error = self._validar(context, dry_run)
        if not valido:
            return {"ok": False, "error": error}

        graph_version = self._graph_version()
        input_token = context.get("input_token")
        app_access_token = self._app_access_token(context) or "***"
        path = "/debug_token"
        params = {"input_token": input_token, "access_token": app_access_token}
        url = self._build_url(graph_version, path, params)

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run",
                "data": {
                    "method": "GET",
                    "graph_version": graph_version,
                    "path": path,
                    "params": {"input_token": input_token, "access_token": "***"},
                    "url": self._build_url(graph_version, path, {"input_token": input_token, "access_token": "***"}),
                },
            }

        try:
            result = self._get(url)
            return {"ok": True, "data": result.get("data", result)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _validar(self, context: dict, dry_run: bool) -> tuple[bool, str | None]:
        if not context.get("input_token"):
            return False, "input_token es requerido"
        if not dry_run and not self._app_access_token(context):
            return False, "app_access_token es requerido, o app_id/app_secret para construir app_id|app_secret"
        return True, None

    def _app_access_token(self, context: dict) -> str | None:
        if context.get("app_access_token"):
            return str(context["app_access_token"])
        app_id = context.get("app_id") or os.getenv("META_APP_ID")
        app_secret = context.get("app_secret") or os.getenv("META_APP_SECRET")
        if app_id and app_secret:
            return f"{app_id}|{app_secret}"
        return None

    def _graph_version(self) -> str:
        return os.getenv("META_GRAPH_API_VERSION", "v24.0")

    def _build_url(self, graph_version: str, path: str, params: dict) -> str:
        return f"https://graph.facebook.com/{graph_version}{path}?" + urllib.parse.urlencode(params)

    def _get(self, url: str) -> dict:
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ValueError(self._error_message(exc)) from exc

    def _error_message(self, exc: urllib.error.HTTPError) -> str:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            return body.get("error", {}).get("message", str(exc))
        except Exception:
            return str(exc)
