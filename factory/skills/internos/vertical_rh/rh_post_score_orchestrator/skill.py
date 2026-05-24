"""Entrypoint for rh_post_score_orchestrator skill."""

from __future__ import annotations

from service import RhPostScoreOrchestratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhPostScoreOrchestratorService().ejecutar(context)
