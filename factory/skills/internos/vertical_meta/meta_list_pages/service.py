"""Service for meta_list_pages - calls Meta Graph API /me/accounts."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_FIELDS = "id,name,access_token,instagram_business_account"


class MetaListPagesService:

    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", False)
        access_token = self._access_token(context)
        if not access_token:
            if not dry_run:
                return {"ok": False, "error": "access_token es requerido en context o META_ACCESS_TOKEN/IG_ACCESS_TOKEN"}
            access_token = "***"

        graph_version = self._graph_version()
        path = "/me/accounts"
        params = {"fields": _FIELDS, "access_token": access_token}
        if context.get("limit"):
            params["limit"] = context["limit"]
        url = self._build_url(graph_version, path, params)

        if dry_run:
            dry_params = dict(params)
            dry_params["access_token"] = "***"
            return {
                "ok": True,
                "message": "dry_run",
                "data": {
                    "method": "GET",
                    "graph_version": graph_version,
                    "path": path,
                    "params": dry_params,
                    "url": self._build_url(graph_version, path, dry_params),
                },
            }

        try:
            result = self._get(url)
            return {"ok": True, "data": {"pages": result.get("data", []), "paging": result.get("paging")}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

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
