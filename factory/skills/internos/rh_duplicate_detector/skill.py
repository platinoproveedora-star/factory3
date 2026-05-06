"""Entrypoint for rh_duplicate_detector skill."""

from __future__ import annotations

from service import RhDuplicateDetectorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhDuplicateDetectorService().ejecutar(context)
