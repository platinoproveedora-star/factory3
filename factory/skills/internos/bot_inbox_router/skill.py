"""Entrypoint for bot_inbox_router skill."""

from __future__ import annotations

from service import BotInboxRouterService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return BotInboxRouterService().ejecutar(context)
