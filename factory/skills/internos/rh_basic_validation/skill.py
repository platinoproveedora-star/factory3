"""Entrypoint for rh_basic_validation skill."""

from __future__ import annotations

from service import RhBasicValidationService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhBasicValidationService().ejecutar(context)
