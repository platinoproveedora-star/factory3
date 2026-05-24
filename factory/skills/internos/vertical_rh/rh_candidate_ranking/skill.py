"""Entrypoint for rh_candidate_ranking skill."""

from __future__ import annotations

from service import RhCandidateRankingService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhCandidateRankingService().ejecutar(context)
