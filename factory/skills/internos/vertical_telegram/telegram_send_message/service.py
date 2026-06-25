"""Service for telegram_send_message - sends a message via Telegram bot."""
from __future__ import annotations
import json
import os
import urllib.request


class TelegramSendMessageService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        if not self._chat_id(context):
            return False, "chat_id es requerido o configura chat_id_env"
        if not context.get("text"):
            return False, "text es requerido"
        token = self._token(context)
        if not token:
            return False, "token es requerido o configura token_env"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        token = self._token(context)
        payload: dict = {
            "chat_id": self._chat_id(context),
            "text": context["text"],
        }
        if context.get("parse_mode"):
            payload["parse_mode"] = context["parse_mode"]
        if context.get("disable_notification"):
            payload["disable_notification"] = context["disable_notification"]
        if context.get("reply_to_message_id"):
            payload["reply_to_message_id"] = context["reply_to_message_id"]
        try:
            result = self._request(token, "sendMessage", payload=payload)
            msg = result.get("result", {})
            return {
                "ok": result.get("ok", False),
                "data": {
                    "message_id": msg.get("message_id"),
                    "chat_id": msg.get("chat", {}).get("id"),
                    "text": msg.get("text", ""),
                    "date": msg.get("date"),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, token: str, method: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/{method}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _token(self, context: dict) -> str:
        token_env = str(context.get("token_env") or "").strip()
        return str(context.get("token") or (os.getenv(token_env) if token_env else "") or os.getenv("TELEGRAM_TOKEN") or "").strip()

    def _chat_id(self, context: dict) -> str:
        chat_id_env = str(context.get("chat_id_env") or "").strip()
        return str(context.get("chat_id") or (os.getenv(chat_id_env) if chat_id_env else "") or "").strip()
