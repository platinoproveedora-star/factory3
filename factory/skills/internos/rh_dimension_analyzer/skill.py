"""Entrypoint for the portable rh_dimension_analyzer skill."""

from __future__ import annotations
from typing import Any
from service import RhDimensionAnalyzerService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhDimensionAnalyzerService().ejecutar(context)
