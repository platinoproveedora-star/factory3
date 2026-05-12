"""Service for meta_refresh_connection - reloads Meta page and IG account metadata."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class MetaRefreshConnectionService:

    def ejecutar(self, context: dict) -> dict:
        access_token = self._get_text(context, "access_token") or os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN")
        page_id = self._get_text(context, "page_id") or os.getenv("META_PAGE_ID") or os.getenv("IG_PAGE_ID")
        graph_version = self._graph_version(context)
        app_id = self._get_text(context, "app_id") or os.getenv("META_APP_ID")
        app_secret = self._get_text(context, "app_secret") or os.getenv("META_APP_SECRET")

        if not access_token:
            return {"ok": False, "error": "access_token es requerido en context, META_ACCESS_TOKEN o IG_ACCESS_TOKEN"}
        if not page_id:
            return {"ok": False, "error": "page_id es requerido en context, META_PAGE_ID o IG_PAGE_ID"}
        if context.get("dry_run", False):
            return {
                "ok": True,
                "message": "dry_run",
                "data": {
                    "graph_version": graph_version,
                    "page_id": page_id,
                    "will_debug_token": bool(app_id and app_secret),
                },
            }

        try:
            page = self._call_meta(
                "GET",
                f"/{page_id}",
                access_token,
                graph_version,
                {"fields": "id,name,access_token,instagram_business_account{id,username,account_type}"},
            )
            ig_account = page.get("instagram_business_account") or {}
            ig_user_id = self._get_text(context, "ig_user_id") or ig_account.get("id")
            ig = {}
            if ig_user_id:
                ig = self._call_meta(
                    "GET",
                    f"/{ig_user_id}",
                    access_token,
                    graph_version,
                    {"fields": "id,username,account_type"},
                )

            token_debug = None
            if app_id and app_secret:
                token_debug = self._debug_token(access_token, graph_version, app_id, app_secret)

            return {
                "ok": True,
                "data": {
                    "graph_version": graph_version,
                    "page": page,
                    "ig_user_id": ig_user_id,
                    "instagram_business_account": ig,
                    "token_debug": token_debug,
                },
            }
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": self._http_error_message(exc)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _debug_token(self, input_token: str, graph_version: str, app_id: str, app_secret: str) -> dict:
        app_access_token = f"{app_id}|{app_secret}"
        params = {"input_token": input_token, "access_token": app_access_token}
        url = f"https://graph.facebook.com/{graph_version}/debug_token?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result.get("data", result)

    def _call_meta(self, method: str, path: str, access_token: str, graph_version: str, params: dict | None = None) -> dict:
        query = {"access_token": access_token}
        if params:
            query.update(params)
        url = f"https://graph.facebook.com/{graph_version}{path}?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, method=method.upper())
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

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
