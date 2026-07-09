from __future__ import annotations
from service import Wabiz24hWindowGuardService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return Wabiz24hWindowGuardService().ejecutar(context)
