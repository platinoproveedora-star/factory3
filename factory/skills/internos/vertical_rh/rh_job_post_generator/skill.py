"""Entrypoint for rh_job_post_generator skill."""

from __future__ import annotations

from service import RhJobPostGeneratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhJobPostGeneratorService().ejecutar(context)
