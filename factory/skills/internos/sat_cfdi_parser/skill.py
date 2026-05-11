from __future__ import annotations
from service import SatCfdiParserService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return SatCfdiParserService().ejecutar(context)
