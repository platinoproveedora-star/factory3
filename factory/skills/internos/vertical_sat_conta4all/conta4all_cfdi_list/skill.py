from __future__ import annotations
from service import Conta4allCfdiListService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return Conta4allCfdiListService().ejecutar(context)
