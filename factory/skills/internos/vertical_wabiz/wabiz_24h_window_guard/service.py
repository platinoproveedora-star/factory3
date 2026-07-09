"""Verifica si el último mensaje entrante del usuario cayó dentro de la ventana de 24h de Meta."""
from __future__ import annotations
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

_UA = "FactoryFactory/0.1 (+https://github.com/)"
_WINDOW_HOURS = 24


class Wabiz24hWindowGuardService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id")
        phone = context.get("phone") or context.get("from_phone") or context.get("to")

        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not phone:
            return {"ok": False, "error": "phone (o from_phone/to) requerido"}

        last = self._last_inbound(empresa_id, phone)
        if last is None:
            return {"ok": True, "data": {"within_window": False, "last_inbound_at": None, "hours_since": None}}

        now = dt.datetime.now(dt.timezone.utc)
        hours_since = (now - last).total_seconds() / 3600
        return {"ok": True, "data": {
            "within_window": hours_since < _WINDOW_HOURS,
            "last_inbound_at": last.isoformat().replace("+00:00", "Z"),
            "hours_since": round(hours_since, 2),
        }}

    def _last_inbound(self, empresa_id: str, phone: str) -> dt.datetime | None:
        qs = urllib.parse.urlencode({
            "empresa_id": f"eq.{empresa_id}",
            "from_phone": f"eq.{phone}",
            "direction": "eq.in",
            "select": "timestamp",
            "order": "timestamp.desc",
            "limit": "1",
        })
        base = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        req = urllib.request.Request(f"{base}/rest/v1/wabiz_messages?{qs}", headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": _UA,
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                if not rows:
                    return None
                return dt.datetime.fromisoformat(rows[0]["timestamp"].replace("Z", "+00:00"))
        except Exception:
            return None
