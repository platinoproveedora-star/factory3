"""Entrypoint for rh_stats skill."""
from __future__ import annotations
from service import RhStatsService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhStatsService().ejecutar(context)
