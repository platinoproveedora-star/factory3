"""Service for telegram_get_bot_info - validates a bot token and returns bot info."""
from __future__ import annotations
import json
import os
import urllib.request


class TelegramGetBotInfoService:

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
        token = context.get("token") or os.getenv("TELEGRAM_TOKEN")
        if not token:
            return False, "token es requerido o configura TELEGRAM_TOKEN"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        token = context.get("token") or os.getenv("TELEGRAM_TOKEN")
        try:
            result = self._request(token, "getMe")
            bot = result.get("result", {})
            return {
                "ok": True,
                "data": {
                    "id": bot.get("id"),
                    "username": bot.get("username"),
                    "first_name": bot.get("first_name"),
                    "is_bot": bot.get("is_bot"),
                    "can_join_groups": bot.get("can_join_groups"),
                    "can_read_all_group_messages": bot.get("can_read_all_group_messages"),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, token: str, method: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/{method}",
            data=data,
            method="POST" if payload else "GET",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
