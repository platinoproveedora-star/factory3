"""Entrypoint for rh_1_run skill."""

from __future__ import annotations

from service import Rh1RunService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return Rh1RunService().ejecutar(context)
