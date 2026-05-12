"""Entrypoint for the portable ig_get_post_insights skill."""
from __future__ import annotations
from typing import Any
from service import IgGetPostInsightsService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return IgGetPostInsightsService().ejecutar(context)
