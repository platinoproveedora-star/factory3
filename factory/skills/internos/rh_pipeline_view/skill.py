"""Entrypoint for rh_pipeline_view skill."""
from __future__ import annotations
from service import RhPipelineViewService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhPipelineViewService().ejecutar(context)
