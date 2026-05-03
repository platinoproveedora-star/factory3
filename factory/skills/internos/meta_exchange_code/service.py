"""Service for meta_exchange_code - exchanges an OAuth code for a Meta access token."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_GRAPH_API_VERSION = "v24.0"


class MetaExchangeCodeService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        request_data = self._build_request_data(context)
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": request_data}
        return self._ejecutar(request_data)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        for key, env_key in (
            ("app_id", "META_APP_ID"),
            ("app_secret", "META_APP_SECRET"),
            ("redirect_uri", "META_REDIRECT_URI"),
        ):
            value = self._get_config(context, key, env_key)
            if not value:
                return False, f"{key} es requerido en context o {env_key} en variables de entorno"
            if not isinstance(value, str):
                return False, f"{key} debe ser texto"
        code = context.get("code")
        if not code or not isinstance(code, str):
            return False, "code es requerido y debe ser texto"
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
            "client_id": self._get_config(context, "app_id", "META_APP_ID"),
            "client_secret": self._get_config(context, "app_secret", "META_APP_SECRET"),
            "redirect_uri": self._get_config(context, "redirect_uri", "META_REDIRECT_URI"),
            "code": context["code"],
        }
        url = f"https://graph.facebook.com/{graph_version}/oauth/access_token?" + urllib.parse.urlencode(params)
        return {"method": "GET", "url": url, "graph_api_version": graph_version, "params": params}

    def _format_token_response(self, result: dict) -> dict:
        data = {
            "access_token": result.get("access_token", ""),
            "token_type": result.get("token_type", "bearer"),
        }
        if "expires_in" in result:
            expires_in = result.get("expires_in", 0)
            data["expires_in"] = expires_in
            if isinstance(expires_in, int):
                data["expires_in_days"] = expires_in // 86400
        return data

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
