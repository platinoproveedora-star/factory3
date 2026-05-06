"""Entrypoint for rh_seed_cleaner skill."""

from __future__ import annotations

from service import RhSeedCleanerService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhSeedCleanerService().ejecutar(context)
