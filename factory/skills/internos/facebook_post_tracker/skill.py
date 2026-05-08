"""Entrypoint for facebook_post_tracker skill."""

from __future__ import annotations

from service import FacebookPostTrackerService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return FacebookPostTrackerService().ejecutar(context)
