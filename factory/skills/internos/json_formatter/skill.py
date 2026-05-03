"""Entrypoint for json_formatter skill."""

from __future__ import annotations

from service import JsonFormatterService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return JsonFormatterService().ejecutar(context)
