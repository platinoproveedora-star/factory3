"""Entrypoint for the portable rh_retention_predictor skill."""
from __future__ import annotations
from typing import Any
from service import RhRetentionPredictorService

def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhRetentionPredictorService().ejecutar(context)
