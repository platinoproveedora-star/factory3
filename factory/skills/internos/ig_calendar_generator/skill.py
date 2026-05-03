"""Entrypoint for the portable ig_calendar_generator skill."""
from __future__ import annotations
from typing import Any
from service import IgCalendarGeneratorService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return IgCalendarGeneratorService().ejecutar(context)
