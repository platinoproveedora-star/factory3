"""Entrypoint for list_deduper skill."""

from __future__ import annotations

from service import ListDeduperService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return ListDeduperService().ejecutar(context)
