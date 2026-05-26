from __future__ import annotations
from service import UpworkClientOrchestratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return UpworkClientOrchestratorService().ejecutar(context)
