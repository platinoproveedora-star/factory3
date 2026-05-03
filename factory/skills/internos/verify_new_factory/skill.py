"""Entrypoint for verify_new_factory skill."""

from __future__ import annotations

from service import VerifyNewFactoryService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return VerifyNewFactoryService().ejecutar(context)
