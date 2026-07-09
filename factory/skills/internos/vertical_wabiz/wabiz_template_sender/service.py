"""Envía un mensaje de plantilla (template) pre-aprobada por Meta vía WhatsApp Cloud API."""
from __future__ import annotations
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

_UA = "FactoryFactory/0.1 (+https://github.com/)"


class WabizTemplateSenderService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id")
        to = str(context.get("to") or "").strip()
        template_name = str(context.get("template_name") or "").strip()
        language_code = context.get("language_code") or "es_MX"
        params = context.get("params") or []

        if not to:
            return {"ok": False, "error": "to (número destino) requerido"}
        if not template_name:
            return {"ok": False, "error": "template_name requerido"}

        cfg = self._load_config(empresa_id) if empresa_id else {}
        token = context.get("access_token") or cfg.get("access_token")
        phone_number_id = context.get("phone_number_id") or cfg.get("phone_number_id")
        graph_version = context.get("graph_version") or cfg.get("graph_version", "v24.0")

        if not token:
            return {"ok": False, "error": f"No hay config para empresa_id={empresa_id}"}
        if not phone_number_id:
            return {"ok": False, "error": "phone_number_id no disponible"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "to": to, "template_name": template_name, "params": params}}

        try:
            result = self._send(phone_number_id, to, template_name, language_code, params, token, graph_version)
            if "error" in result:
                err = result["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            wa_message_id = result.get("messages", [{}])[0].get("id")
            self._log_outbound(empresa_id, to, template_name, wa_message_id)

            return {"ok": True, "data": {"sent": True, "wa_message_id": wa_message_id, "to": to}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _send(self, phone_number_id: str, to: str, template_name: str, language_code: str,
              params: list, token: str, version: str) -> dict:
        components = []
        if params:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in params],
            })

        url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
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

    def _log_outbound(self, empresa_id: str, to: str, template_name: str, wa_message_id: str) -> None:
        if not empresa_id:
            return
        try:
            row = {
                "empresa_id": empresa_id,
                "from_phone": to,
                "direction": "out",
                "type": "template",
                "body": template_name,
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
