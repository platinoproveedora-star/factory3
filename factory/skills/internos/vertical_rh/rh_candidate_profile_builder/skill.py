"""Entrypoint for rh_candidate_profile_builder skill."""

from __future__ import annotations

from service import RhCandidateProfileBuilderService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhCandidateProfileBuilderService().ejecutar(context)
