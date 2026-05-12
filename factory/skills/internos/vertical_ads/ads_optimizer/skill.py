from __future__ import annotations
from service import AdsOptimizerService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return AdsOptimizerService().ejecutar(context)
