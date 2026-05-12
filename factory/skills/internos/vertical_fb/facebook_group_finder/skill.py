"""Entrypoint for facebook_group_finder skill."""

from __future__ import annotations

from service import FacebookGroupFinderService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return FacebookGroupFinderService().ejecutar(context)
