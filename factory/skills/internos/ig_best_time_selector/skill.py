"""Entrypoint for the portable ig_best_time_selector skill."""
from __future__ import annotations
from typing import Any
from service import IgBestTimeSelectorService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return IgBestTimeSelectorService().ejecutar(context)
