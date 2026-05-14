"""Normaliza el payload de webhook Meta WhatsApp al formato interno de la fábrica."""
from __future__ import annotations
import datetime as dt
import json
import os
import urllib.request


class WabizWebhookParseService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id")
        raw        = context.get("body")

        if not raw or not isinstance(raw, dict):
            return {"ok": False, "error": "body requerido (dict con payload Meta)"}
        if raw.get("object") != "whatsapp_business_account":
            return {"ok": False, "error": f"object no soportado: {raw.get('object')}"}

        events = []
        for entry in raw.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "messages":
                    continue
                value           = change.get("value", {})
                phone_number_id = value.get("metadata", {}).get("phone_number_id")

                for msg in value.get("messages", []):
                    events.append(self._parse_message(msg, phone_number_id, empresa_id, value))

                for status in value.get("statuses", []):
                    events.append(self._parse_status(status, phone_number_id, empresa_id))

        if not context.get("dry_run", True):
            self._log_inbound(events)

        return {"ok": True, "data": {"events": events, "count": len(events)}}

    def _parse_message(self, msg: dict, phone_number_id: str, empresa_id: str, value: dict) -> dict:
        msg_type = msg.get("type", "unknown")
        body     = None

        if msg_type == "text":
            body = msg.get("text", {}).get("body", "")
        elif msg_type in {"image", "audio", "video", "document", "sticker"}:
            body = msg.get(msg_type, {}).get("id")  # media_id para descarga posterior
        elif msg_type == "location":
            loc  = msg.get("location", {})
            body = f"{loc.get('latitude')},{loc.get('longitude')}"
        elif msg_type == "interactive":
            reply = msg.get("interactive", {})
            body  = (reply.get("button_reply") or reply.get("list_reply") or {}).get("id", "")
        elif msg_type == "button":
            body = msg.get("button", {}).get("payload", "")

        contacts     = value.get("contacts", [{}])
        profile_name = contacts[0].get("profile", {}).get("name") if contacts else None

        return {
            "kind":            "message",
            "empresa_id":      empresa_id,
            "phone_number_id": phone_number_id,
            "from_phone":      msg.get("from"),
            "profile_name":    profile_name,
            "wa_message_id":   msg.get("id"),
            "type":            msg_type,
            "body":            body,
            "timestamp":       msg.get("timestamp"),
        }

    def _parse_status(self, status: dict, phone_number_id: str, empresa_id: str) -> dict:
        return {
            "kind":            "status",
            "empresa_id":      empresa_id,
            "phone_number_id": phone_number_id,
            "wa_message_id":   status.get("id"),
            "to_phone":        status.get("recipient_id"),
            "status":          status.get("status"),
            "timestamp":       status.get("timestamp"),
        }

    def _log_inbound(self, events: list) -> None:
        rows = []
        for e in events:
            if e.get("kind") != "message" or not e.get("empresa_id") or not e.get("from_phone"):
                continue
            ts_raw = e.get("timestamp")
            try:
                ts = dt.datetime.fromtimestamp(int(ts_raw), tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
            except (TypeError, ValueError):
                ts = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            rows.append({
                "empresa_id":    e["empresa_id"],
                "from_phone":    e["from_phone"],
                "direction":     "in",
                "type":          e["type"],
                "body":          e.get("body"),
                "wa_message_id": e.get("wa_message_id"),
                "timestamp":     ts,
            })
        if not rows:
            return
        try:
            url  = f"{os.getenv('SUPABASE_URL')}/rest/v1/wabiz_messages"
            data = json.dumps(rows).encode()
            req  = urllib.request.Request(
                url, data=data, method="POST",
                headers={
                    "apikey":        os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                    "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')}",
                    "Content-Type":  "application/json",
                    "Prefer":        "return=minimal",
                },
            )
            urllib.request.urlopen(req, timeout=10).close()
        except Exception:
            pass
