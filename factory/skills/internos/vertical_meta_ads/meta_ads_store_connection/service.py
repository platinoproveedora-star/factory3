"""Normaliza y devuelve payload portable de conexión Meta Ads."""
from __future__ import annotations
import datetime as dt
import os


class MetaAdsStoreConnectionService:

    def ejecutar(self, context: dict) -> dict:
        token = self._str(context, "access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = self._str(context, "ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido (ej. act_123456)"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        token_expires_at = self._resolve_expiry(context)
        if token_expires_at is False:
            return {"ok": False, "error": "token_expires_at debe ser ISO-8601 o expires_in debe ser numérico"}

        graph_version = (
            self._str(context, "graph_version")
            or os.getenv("META_GRAPH_API_VERSION", "v24.0")
        )

        payload = {
            "provider":        "meta_ads",
            "access_token":    token,
            "ad_account_id":   ad_account_id,
            "graph_version":   graph_version,
            "token_expires_at": token_expires_at,
            "created_at":      dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        for field in ("nombre_cuenta", "moneda", "zona_horaria", "business_id", "empresa_id", "workspace_id"):
            val = self._str(context, field)
            if val:
                payload[field] = val

        return {"ok": True, "data": {"payload": payload}}

    def _resolve_expiry(self, context: dict):
        explicit = self._str(context, "token_expires_at")
        if explicit:
            try:
                dt.datetime.fromisoformat(explicit.replace("Z", "+00:00"))
                return explicit
            except ValueError:
                return False
        expires_in = context.get("expires_in")
        if expires_in is None:
            return None
        try:
            secs = int(expires_in)
        except (TypeError, ValueError):
            return False
        exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=secs)
        return exp.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _str(self, context: dict, key: str):
        val = context.get(key)
        return val.strip() if isinstance(val, str) and val.strip() else None
