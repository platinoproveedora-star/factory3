from __future__ import annotations
from service import IgListService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return IgListService().ejecutar(context)
