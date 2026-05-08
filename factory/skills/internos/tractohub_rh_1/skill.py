"""Entrypoint for tractohub_rh_1 skill."""

from __future__ import annotations

from service import TractohubRh1Service


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return TractohubRh1Service().ejecutar(context)
