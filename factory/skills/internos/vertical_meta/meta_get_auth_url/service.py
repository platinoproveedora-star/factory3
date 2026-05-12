"""Service for meta_get_auth_url - builds a Meta OAuth authorization URL."""
from __future__ import annotations

import os
import urllib.parse


DEFAULT_GRAPH_API_VERSION = "v24.0"
DEFAULT_SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_content_publish",
    "instagram_manage_comments",
    "instagram_manage_messages",
    "instagram_manage_insights",
]


class MetaGetAuthUrlService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        data = self._build_data(context)
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": data}
        return {"ok": True, "data": data}

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        app_id = self._get_config(context, "app_id", "META_APP_ID")
        redirect_uri = self._get_config(context, "redirect_uri", "META_REDIRECT_URI")
        if not app_id:
            return False, "app_id es requerido en context o META_APP_ID en variables de entorno"
        if not redirect_uri:
            return False, "redirect_uri es requerido en context o META_REDIRECT_URI en variables de entorno"
        if not isinstance(app_id, str):
            return False, "app_id debe ser texto"
        if not isinstance(redirect_uri, str):
            return False, "redirect_uri debe ser texto"
        scopes = context.get("scopes")
        if scopes is not None and not self._normalize_scopes(scopes):
            return False, "scopes debe ser lista de textos o texto separado por comas/espacios"
        return True, None

    def _build_data(self, context: dict) -> dict:
        graph_version = self._get_config(context, "graph_api_version", "META_GRAPH_API_VERSION") or DEFAULT_GRAPH_API_VERSION
        app_id = self._get_config(context, "app_id", "META_APP_ID")
        redirect_uri = self._get_config(context, "redirect_uri", "META_REDIRECT_URI")
        scopes = self._normalize_scopes(context.get("scopes")) or DEFAULT_SCOPES

        params = {
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(scopes),
            "response_type": context.get("response_type", "code"),
        }
        state = context.get("state")
        if state:
            params["state"] = state
        auth_type = context.get("auth_type")
        if auth_type:
            params["auth_type"] = auth_type

        auth_url = f"https://www.facebook.com/{graph_version}/dialog/oauth?" + urllib.parse.urlencode(params)
        return {
            "auth_url": auth_url,
            "graph_api_version": graph_version,
            "app_id": app_id,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
        }

    def _get_config(self, context: dict, key: str, env_key: str) -> str | None:
        value = context.get(key)
        if value is None or value == "":
            value = os.getenv(env_key)
        return value

    def _normalize_scopes(self, scopes: object) -> list[str]:
        if scopes is None:
            return []
        if isinstance(scopes, str):
            raw_scopes = scopes.replace(",", " ").split()
            return [scope.strip() for scope in raw_scopes if scope.strip()]
        if isinstance(scopes, list) and all(isinstance(scope, str) and scope.strip() for scope in scopes):
            return [scope.strip() for scope in scopes]
        return []
