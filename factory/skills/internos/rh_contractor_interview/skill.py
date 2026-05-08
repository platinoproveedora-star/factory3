"""Entrypoint for the portable rh_contractor_interview skill."""

from __future__ import annotations
from typing import Any
from service import RhContractorInterviewService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhContractorInterviewService().ejecutar(context)
