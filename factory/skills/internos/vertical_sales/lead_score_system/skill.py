from __future__ import annotations
from service import LeadScoreService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return LeadScoreService().ejecutar(context)
