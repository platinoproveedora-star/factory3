"""Entrypoint for rh_candidate_history skill."""

from __future__ import annotations

from service import RhCandidateHistoryService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhCandidateHistoryService().ejecutar(context)
