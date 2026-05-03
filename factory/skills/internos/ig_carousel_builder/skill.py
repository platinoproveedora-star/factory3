"""Entrypoint for the portable ig_carousel_builder skill."""
from __future__ import annotations
from typing import Any
from service import IgCarouselBuilderService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return IgCarouselBuilderService().ejecutar(context)
