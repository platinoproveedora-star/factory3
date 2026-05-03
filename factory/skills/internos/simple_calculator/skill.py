"""Entrypoint for simple_calculator skill."""

from __future__ import annotations

from service import SimpleCalculatorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SimpleCalculatorService().ejecutar(context)
