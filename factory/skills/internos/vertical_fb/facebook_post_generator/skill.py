"""Entrypoint for facebook_post_generator skill."""

from __future__ import annotations

from service import FacebookPostGeneratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return FacebookPostGeneratorService().ejecutar(context)
