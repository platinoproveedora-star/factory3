"""Service for telegram_set_webhook - sets the webhook URL for a Telegram bot."""
from __future__ import annotations
import json
import os
import urllib.request


class TelegramSetWebhookService:

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
        if not context.get("url"):
            return False, "url es requerido (URL publica del webhook)"
        token = context.get("token") or os.getenv("TELEGRAM_TOKEN")
        if not token:
            return False, "token es requerido o configura TELEGRAM_TOKEN"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        token = context.get("token") or os.getenv("TELEGRAM_TOKEN")
        payload: dict = {"url": context["url"]}
        if context.get("secret_token"):
            payload["secret_token"] = context["secret_token"]
        if context.get("max_connections"):
            payload["max_connections"] = context["max_connections"]
        if context.get("allowed_updates"):
            payload["allowed_updates"] = context["allowed_updates"]
        try:
            result = self._request(token, "setWebhook", payload=payload)
            return {
                "ok": result.get("ok", False),
                "message": result.get("description", "Webhook configurado"),
                "data": {"url": context["url"], "result": result.get("result")},
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
