"""Service for meta_get_instagram_account - reads IG account linked to a Page."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_FIELDS = "instagram_business_account{id,username,name,profile_picture_url}"


class MetaGetInstagramAccountService:

    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", False)
        valido, error = self._validar(context, dry_run)
        if not valido:
            return {"ok": False, "error": error}

        access_token = self._access_token(context) or "***"
        graph_version = self._graph_version()
        page_id = context["page_id"]
        path = f"/{page_id}"
        params = {"fields": _FIELDS, "access_token": access_token}
        url = self._build_url(graph_version, path, params)

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run",
                "data": {
                    "method": "GET",
                    "graph_version": graph_version,
                    "path": path,
                    "params": {"fields": _FIELDS, "access_token": "***"},
                    "url": self._build_url(graph_version, path, {"fields": _FIELDS, "access_token": "***"}),
                },
            }

        try:
            result = self._get(url)
            return {
                "ok": True,
                "data": {
                    "page_id": result.get("id", page_id),
                    "instagram_business_account": result.get("instagram_business_account"),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _validar(self, context: dict, dry_run: bool) -> tuple[bool, str | None]:
        if not context.get("page_id"):
            return False, "page_id es requerido"
        if not dry_run and not self._access_token(context):
            return False, "access_token es requerido en context o META_ACCESS_TOKEN/IG_ACCESS_TOKEN"
        return True, None

    def _access_token(self, context: dict) -> str | None:
        return context.get("access_token") or os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN")

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
