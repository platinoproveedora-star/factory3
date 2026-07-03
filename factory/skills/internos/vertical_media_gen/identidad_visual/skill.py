"""Entrypoint for identidad_visual skill."""
from __future__ import annotations
from service import IdentidadVisualService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return IdentidadVisualService().ejecutar(context)
