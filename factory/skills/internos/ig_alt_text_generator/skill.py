"""Entrypoint for the portable ig_alt_text_generator skill."""
from __future__ import annotations
from typing import Any
from service import IgAltTextGeneratorService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return IgAltTextGeneratorService().ejecutar(context)
