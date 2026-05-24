"""Entrypoint for whatsapp_group_broadcaster skill."""

from __future__ import annotations

from service import WhatsappGroupBroadcasterService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return WhatsappGroupBroadcasterService().ejecutar(context)
