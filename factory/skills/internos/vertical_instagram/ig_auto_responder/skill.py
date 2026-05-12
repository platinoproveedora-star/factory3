from __future__ import annotations
from service import IgAutoResponderService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return IgAutoResponderService().ejecutar(context)
