"""Sube o referencia un archivo y lo envía por WhatsApp Cloud API. Registra en wabiz_messages."""
from __future__ import annotations
import base64
import datetime as dt
import json
import os
import urllib.parse
import urllib.request
import uuid

_UA = "FactoryFactory/0.1 (+https://github.com/)"
_GRAPH_BASE = "https://graph.facebook.com"
_VALID_TYPES = {"image", "document", "audio", "video"}


class WabizSendMediaService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id")
        to = str(context.get("to") or "").strip()
        media_type = str(context.get("media_type") or "").strip().lower()
        content_b64 = context.get("content_b64")
        link = str(context.get("link") or "").strip()
        mime_type = context.get("mime_type") or "application/octet-stream"
        filename = context.get("filename")
        caption = context.get("caption")

        if not to:
            return {"ok": False, "error": "to (número destino) requerido"}
        if media_type not in _VALID_TYPES:
            return {"ok": False, "error": f"media_type debe ser uno de {sorted(_VALID_TYPES)}"}
        if not content_b64 and not link:
            return {"ok": False, "error": "content_b64 o link requerido"}

        cfg = self._load_config(empresa_id) if empresa_id else {}
        token = context.get("access_token") or cfg.get("access_token")
        phone_number_id = context.get("phone_number_id") or cfg.get("phone_number_id")
        graph_version = context.get("graph_version") or cfg.get("graph_version", "v24.0")

        if not token:
            return {"ok": False, "error": f"No hay config para empresa_id={empresa_id}"}
        if not phone_number_id:
            return {"ok": False, "error": "phone_number_id no disponible"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "to": to, "media_type": media_type}}

        try:
            media_id = None
            if content_b64:
                upload = self._upload_media(phone_number_id, content_b64, mime_type, filename, token, graph_version)
                if not upload.get("ok"):
                    return upload
                media_id = upload["data"]["media_id"]

            result = self._send(phone_number_id, to, media_type, media_id, link, filename, caption, token, graph_version)
            if "error" in result:
                err = result["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            wa_message_id = result.get("messages", [{}])[0].get("id")
            self._log_outbound(empresa_id, to, media_type, filename or link, wa_message_id)

            return {"ok": True, "data": {"sent": True, "wa_message_id": wa_message_id, "media_id": media_id, "to": to}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _upload_media(self, phone_number_id: str, content_b64: str, mime_type: str, filename: str | None, token: str, version: str) -> dict:
        try:
            content_bytes = base64.b64decode(content_b64)
        except Exception as e:
            return {"ok": False, "error": f"content_b64 inválido: {e}"}

        boundary = f"----FactoryWabiz{uuid.uuid4().hex}"
        name = filename or "file"
        parts = [
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="messaging_product"\r\n\r\n'
            f"whatsapp\r\n".encode(),
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="type"\r\n\r\n'
            f"{mime_type}\r\n".encode(),
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n".encode()
            + content_bytes
            + b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        body = b"".join(parts)

        url = f"{_GRAPH_BASE}/{version}/{phone_number_id}/media"
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": _UA,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
                if "id" not in data:
                    return {"ok": False, "error": f"Respuesta sin media id: {data}"}
                return {"ok": True, "data": {"media_id": data["id"]}}
        except Exception as e:
            return {"ok": False, "error": f"Error subiendo media: {e}"}

    def _send(self, phone_number_id: str, to: str, media_type: str, media_id: str | None, link: str,
              filename: str | None, caption: str | None, token: str, version: str) -> dict:
        media_obj: dict = {"id": media_id} if media_id else {"link": link}
        if caption and media_type in ("image", "video", "document"):
            media_obj["caption"] = caption
        if filename and media_type == "document":
            media_obj["filename"] = filename

        url = f"{_GRAPH_BASE}/{version}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": media_type,
            media_type: media_obj,
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

    def _log_outbound(self, empresa_id: str, to: str, media_type: str, body: str | None, wa_message_id: str) -> None:
        if not empresa_id:
            return
        try:
            row = {
                "empresa_id": empresa_id,
                "from_phone": to,
                "direction": "out",
                "type": media_type,
                "body": body or "",
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
