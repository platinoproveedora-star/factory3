"""Entrypoint for facebook_post_publisher skill."""

from __future__ import annotations

from service import FacebookPostPublisherService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return FacebookPostPublisherService().ejecutar(context)
