"""Service for meta_extend_token - exchanges a short-lived Meta token for a long-lived token."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_GRAPH_API_VERSION = "v24.0"


class MetaExtendTokenService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        request_data = self._build_request_data(context)
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": request_data}
        return self._ejecutar(request_data)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        for key, env_key in (("app_id", "META_APP_ID"), ("app_secret", "META_APP_SECRET")):
            value = self._get_config(context, key, env_key)
            if not value:
                return False, f"{key} es requerido en context o {env_key} en variables de entorno"
            if not isinstance(value, str):
                return False, f"{key} debe ser texto"
        access_token = context.get("access_token") or context.get("short_lived_token")
        if not access_token or not isinstance(access_token, str):
            return False, "access_token es requerido y debe ser texto"
        return True, None

    def _ejecutar(self, request_data: dict) -> dict:
        try:
            req = urllib.request.Request(request_data["url"], method="GET")
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            return {"ok": True, "data": self._format_token_response(result)}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": self._read_http_error(exc)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _build_request_data(self, context: dict) -> dict:
        graph_version = self._get_config(context, "graph_api_version", "META_GRAPH_API_VERSION") or DEFAULT_GRAPH_API_VERSION
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self._get_config(context, "app_id", "META_APP_ID"),
            "client_secret": self._get_config(context, "app_secret", "META_APP_SECRET"),
            "fb_exchange_token": context.get("access_token") or context.get("short_lived_token"),
        }
        url = f"https://graph.facebook.com/{graph_version}/oauth/access_token?" + urllib.parse.urlencode(params)
        return {"method": "GET", "url": url, "graph_api_version": graph_version, "params": params}

    def _format_token_response(self, result: dict) -> dict:
        expires_in = result.get("expires_in", 0)
        return {
            "access_token": result.get("access_token", ""),
            "token_type": result.get("token_type", "bearer"),
            "expires_in": expires_in,
            "expires_in_days": expires_in // 86400 if isinstance(expires_in, int) else None,
        }

    def _get_config(self, context: dict, key: str, env_key: str) -> str | None:
        value = context.get(key)
        if value is None or value == "":
            value = os.getenv(env_key)
        return value

    def _read_http_error(self, exc: urllib.error.HTTPError) -> str:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            return body.get("error", {}).get("message", str(exc))
        except Exception:
            return str(exc)
