"""Entrypoint for rh_knockout_filter skill."""

from __future__ import annotations

from service import RhKnockoutFilterService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhKnockoutFilterService().ejecutar(context)
