"""Envía mensajes interactivos (botones o lista) vía WhatsApp Cloud API. Registra en wabiz_messages."""
from __future__ import annotations
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

_UA = "FactoryFactory/0.1 (+https://github.com/)"
_MAX_BUTTONS = 3
_MAX_ROWS = 10
_TITLE_MAX = 20


class WabizSendInteractiveService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id")
        to = str(context.get("to") or "").strip()
        body = str(context.get("body") or "").strip()
        interactive_type = str(context.get("interactive_type") or "").strip().lower()

        if not to:
            return {"ok": False, "error": "to (número destino) requerido"}
        if not body:
            return {"ok": False, "error": "body (texto del mensaje) requerido"}
        if interactive_type not in ("button", "list"):
            return {"ok": False, "error": "interactive_type debe ser 'button' o 'list'"}

        if interactive_type == "button":
            buttons = context.get("buttons") or []
            if not buttons or len(buttons) > _MAX_BUTTONS:
                return {"ok": False, "error": f"buttons requerido, máximo {_MAX_BUTTONS}"}
            action = {"buttons": [
                {"type": "reply", "reply": {"id": str(b["id"]), "title": str(b["title"])[:_TITLE_MAX]}}
                for b in buttons
            ]}
        else:
            rows = context.get("rows") or []
            if not rows or len(rows) > _MAX_ROWS:
                return {"ok": False, "error": f"rows requerido, máximo {_MAX_ROWS}"}
            button_label = str(context.get("button_label") or "Elegir")[:_TITLE_MAX]
            section_title = str(context.get("section_title") or "Opciones")
            action = {
                "button": button_label,
                "sections": [{
                    "title": section_title,
                    "rows": [
                        {
                            "id": str(r["id"]),
                            "title": str(r["title"])[:_TITLE_MAX],
                            **({"description": str(r["description"])[:72]} if r.get("description") else {}),
                        }
                        for r in rows
                    ],
                }],
            }

        cfg = self._load_config(empresa_id) if empresa_id else {}
        token = context.get("access_token") or cfg.get("access_token")
        phone_number_id = context.get("phone_number_id") or cfg.get("phone_number_id")
        graph_version = context.get("graph_version") or cfg.get("graph_version", "v24.0")

        if not token:
            return {"ok": False, "error": f"No hay config para empresa_id={empresa_id}"}
        if not phone_number_id:
            return {"ok": False, "error": "phone_number_id no disponible"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "to": to, "interactive_type": interactive_type}}

        try:
            result = self._send(phone_number_id, to, interactive_type, body, action, token, graph_version)
            if "error" in result:
                err = result["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            wa_message_id = result.get("messages", [{}])[0].get("id")
            self._log_outbound(empresa_id, to, interactive_type, body, wa_message_id)

            return {"ok": True, "data": {"sent": True, "wa_message_id": wa_message_id, "to": to}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _send(self, phone_number_id: str, to: str, interactive_type: str, body: str, action: dict,
              token: str, version: str) -> dict:
        url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": interactive_type,
                "body": {"text": body},
                "action": action,
            },
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": _UA,
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def _load_config(self, empresa_id: str) -> dict:
        try:
            qs = urllib.parse.urlencode({
                "empresa_id": f"eq.{empresa_id}",
                "select": "access_token,phone_number_id,graph_version",
                "limit": "1",
            })
            url = f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/wabiz_config?{qs}"
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            req = urllib.request.Request(url, headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
                "User-Agent": _UA,
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read().decode())
                return rows[0] if rows else {}
        except Exception:
            return {}

    def _log_outbound(self, empresa_id: str, to: str, interactive_type: str, body: str, wa_message_id: str) -> None:
        if not empresa_id:
            return
        try:
            row = {
                "empresa_id": empresa_id,
                "from_phone": to,
                "direction": "out",
                "type": f"interactive_{interactive_type}",
                "body": body,
                "wa_message_id": wa_message_id,
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            url = f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/wabiz_messages"
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            data = json.dumps(row).encode()
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                    "User-Agent": _UA,
                },
            )
            urllib.request.urlopen(req, timeout=10).close()
        except Exception:
            pass
