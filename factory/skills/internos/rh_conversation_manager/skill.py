"""Entrypoint for rh_conversation_manager skill."""

from __future__ import annotations

from service import RhConversationManagerService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhConversationManagerService().ejecutar(context)
