"""Entrypoint for text_cleaner skill."""

from __future__ import annotations

from service import TextCleanerService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return TextCleanerService().ejecutar(context)
