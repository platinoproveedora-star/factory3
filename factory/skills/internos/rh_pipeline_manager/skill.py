"""Entrypoint for rh_pipeline_manager skill."""

from __future__ import annotations

from service import RhPipelineManagerService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhPipelineManagerService().ejecutar(context)
