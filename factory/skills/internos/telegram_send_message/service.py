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
        for field in ("chat_id", "text"):
            if not context.get(field):
                return False, f"{field} es requerido"
        token = context.get("token") or os.getenv("TELEGRAM_TOKEN")
        if not token:
            return False, "token es requerido o configura TELEGRAM_TOKEN"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        token = context.get("token") or os.getenv("TELEGRAM_TOKEN")
        payload: dict = {
            "chat_id": context["chat_id"],
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
