"""Entrypoint for rh_interview_simulator skill."""
from __future__ import annotations
from service import RhInterviewSimulatorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhInterviewSimulatorService().ejecutar(context)
