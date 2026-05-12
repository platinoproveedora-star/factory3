"""Service for meta_store_connection - validates and normalizes portable connection data."""
from __future__ import annotations

import datetime as dt
import os


class MetaStoreConnectionService:

    def ejecutar(self, context: dict) -> dict:
        access_token = self._get_text(context, "access_token") or os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN")
        page_id = self._get_text(context, "page_id") or os.getenv("META_PAGE_ID") or os.getenv("IG_PAGE_ID")
        ig_user_id = (
            self._get_text(context, "ig_user_id")
            or self._get_text(context, "instagram_business_account")
            or os.getenv("META_IG_USER_ID")
            or os.getenv("IG_BUSINESS_ACCOUNT_ID")
        )
        if not access_token:
            return {"ok": False, "error": "access_token es requerido en context, META_ACCESS_TOKEN o IG_ACCESS_TOKEN"}
        if not page_id:
            return {"ok": False, "error": "page_id es requerido en context, META_PAGE_ID o IG_PAGE_ID"}
        if not ig_user_id:
            return {"ok": False, "error": "ig_user_id o instagram_business_account es requerido"}

        token_expires_at = self._token_expires_at(context)
        if token_expires_at is False:
            return {"ok": False, "error": "token_expires_at debe ser ISO-8601 o expires_in debe ser numerico"}

        payload = {
            "provider": "meta",
            "access_token": access_token,
            "token_expires_at": token_expires_at,
            "page_id": page_id,
            "ig_user_id": ig_user_id,
            "scopes": sorted(self._normalize_scopes(context.get("scopes") or context.get("permissions") or context.get("permisos"))),
            "graph_version": self._graph_version(context),
        }
        optional_fields = ("page_name", "ig_username", "account_id", "workspace_id", "connection_id")
        for field in optional_fields:
            value = self._get_text(context, field)
            if value:
                payload[field] = value

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": {"payload": payload}}
        return {"ok": True, "data": {"payload": payload}}

    def _token_expires_at(self, context: dict) -> str | None | bool:
        explicit = self._get_text(context, "token_expires_at")
        if explicit:
            return explicit if self._is_iso_datetime(explicit) else False
        expires_in = context.get("expires_in")
        if expires_in in (None, ""):
            return None
        try:
            seconds = int(expires_in)
        except (TypeError, ValueError):
            return False
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)
        return expires_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _is_iso_datetime(self, value: str) -> bool:
        try:
            dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    def _normalize_scopes(self, value: object) -> set[str]:
        if isinstance(value, str):
            return {part.strip() for part in value.replace(" ", ",").split(",") if part.strip()}
        if isinstance(value, (list, tuple, set)):
            return {str(item).strip() for item in value if str(item).strip()}
        return set()

    def _get_text(self, context: dict, key: str) -> str | None:
        value = context.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _graph_version(self, context: dict) -> str:
        return self._get_text(context, "graph_version") or os.getenv("META_GRAPH_API_VERSION") or os.getenv("IG_GRAPH_API_VERSION") or "v24.0"
