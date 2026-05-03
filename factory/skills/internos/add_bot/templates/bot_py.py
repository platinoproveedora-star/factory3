def render() -> str:
    return '''"""Runtime entrypoint for this Factory bot."""

from __future__ import annotations

from tools import responder_comando


def handle_update(update: dict) -> dict:
    if not isinstance(update, dict):
        return {"ok": False, "error": "update debe ser diccionario"}
    message = update.get("message", {})
    text = message.get("text", "")
    command = text.split()[0].lstrip("/") if text.startswith("/") else "message"
    response = responder_comando(command, text)
    return {
        "ok": True,
        "command": command,
        "response": response,
    }
'''
