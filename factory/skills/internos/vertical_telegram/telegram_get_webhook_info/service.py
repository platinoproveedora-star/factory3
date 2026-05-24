"""Service for telegram_get_webhook_info - returns current webhook configuration."""
from __future__ import annotations
import json
import os
import urllib.request


class TelegramGetWebhookInfoService:

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
            result = self._request(token, "getWebhookInfo")
            info = result.get("result", {})
            configured = bool(info.get("url"))
            return {
                "ok": True,
                "data": {
                    "configured": configured,
                    "url": info.get("url", ""),
                    "pending_update_count": info.get("pending_update_count", 0),
                    "last_error_message": info.get("last_error_message", ""),
                    "last_error_date": info.get("last_error_date"),
                    "max_connections": info.get("max_connections"),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, token: str, method: str) -> dict:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/{method}",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
