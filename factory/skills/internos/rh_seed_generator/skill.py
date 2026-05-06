"""Entrypoint for rh_seed_generator skill."""

from __future__ import annotations

from service import RhSeedGeneratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhSeedGeneratorService().ejecutar(context)
