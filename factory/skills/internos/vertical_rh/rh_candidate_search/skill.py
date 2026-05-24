"""Entrypoint for rh_candidate_search skill."""

from __future__ import annotations

from service import RhCandidateSearchService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhCandidateSearchService().ejecutar(context)
