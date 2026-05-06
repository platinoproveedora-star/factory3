"""Entrypoint for bot_form_capture skill."""

from __future__ import annotations

from service import BotFormCaptureService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return BotFormCaptureService().ejecutar(context)
