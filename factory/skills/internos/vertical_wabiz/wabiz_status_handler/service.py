"""Procesa eventos de status (sent/delivered/read/failed) y actualiza wabiz_messages."""
from __future__ import annotations
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

_UA = "FactoryFactory/0.1 (+https://github.com/)"


class WabizStatusHandlerService:

    def ejecutar(self, context: dict) -> dict:
        wa_message_id = context.get("wa_message_id")
        status = context.get("status")

        if not wa_message_id:
            return {"ok": False, "error": "wa_message_id requerido"}
        if not status:
            return {"ok": False, "error": "status requerido"}

        ts_raw = context.get("timestamp")
        try:
            status_updated_at = dt.datetime.fromtimestamp(int(ts_raw), tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError):
            status_updated_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "wa_message_id": wa_message_id, "status": status}}

        updated = self._update_status(wa_message_id, status, status_updated_at)
        if not updated.get("ok"):
            return updated

        return {"ok": True, "data": {"wa_message_id": wa_message_id, "status": status, "rows_updated": updated["rows"]}}

    def _update_status(self, wa_message_id: str, status: str, status_updated_at: str) -> dict:
        base = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        qs = urllib.parse.urlencode({"wa_message_id": f"eq.{wa_message_id}"})
        url = f"{base}/rest/v1/wabiz_messages?{qs}"
        payload = json.dumps({"status": status, "status_updated_at": status_updated_at}).encode()
        req = urllib.request.Request(
            url, data=payload, method="PATCH",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal,count=exact",
                "User-Agent": _UA,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                cr = r.headers.get("Content-Range", "*/0")
            rows = int(cr.split("/")[-1]) if "/" in cr else 0
            return {"ok": True, "rows": rows}
        except Exception as e:
            return {"ok": False, "error": f"Error actualizando status: {e}"}
