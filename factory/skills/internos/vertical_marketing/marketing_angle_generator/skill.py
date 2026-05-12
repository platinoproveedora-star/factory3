from __future__ import annotations
from service import MarketingAngleGeneratorService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return MarketingAngleGeneratorService().ejecutar(context)
