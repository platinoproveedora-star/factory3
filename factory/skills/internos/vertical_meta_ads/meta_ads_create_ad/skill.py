from __future__ import annotations
from service import MetaAdsCreateAdService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return MetaAdsCreateAdService().ejecutar(context)
