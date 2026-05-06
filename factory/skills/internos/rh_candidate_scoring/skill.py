"""Entrypoint for rh_candidate_scoring skill."""

from __future__ import annotations

from service import RhCandidateScoringService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhCandidateScoringService().ejecutar(context)
