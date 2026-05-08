"""Entrypoint for facebook_marketplace_poster skill."""

from __future__ import annotations

from service import FacebookMarketplacePosterService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return FacebookMarketplacePosterService().ejecutar(context)
