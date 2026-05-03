"""Admin bot for factory."""
from __future__ import annotations

COMMANDS = {
    "/start": "Hola! Soy el bot admin de esta fabrica. Escribe /ayuda para ver los comandos.",
    "/ayuda": "Comandos disponibles:\n/start - Iniciar\n/ayuda - Ayuda\n/estado - Estado de la fabrica",
    "/estado": "Fabrica activa y funcionando.",
}

def handle_update(update: dict, state: dict) -> dict:
    message = update.get("message", {})
    text = (message.get("text") or "").strip()
    response = COMMANDS.get(text, "Comando no reconocido. Escribe /ayuda para ver los comandos disponibles.")
    return {
        "response": response,
        "state": {},
        "command": text.lstrip("/") if text.startswith("/") else None,
    }
