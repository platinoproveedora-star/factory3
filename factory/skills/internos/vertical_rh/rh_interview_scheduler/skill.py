"""Entrypoint for the portable rh_interview_scheduler skill."""

from __future__ import annotations
from typing import Any
from service import RhInterviewSchedulerService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhInterviewSchedulerService().ejecutar(context)
