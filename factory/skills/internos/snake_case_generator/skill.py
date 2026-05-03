"""Entrypoint for snake_case_generator skill."""

from __future__ import annotations

from service import SnakeCaseGeneratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SnakeCaseGeneratorService().ejecutar(context)
