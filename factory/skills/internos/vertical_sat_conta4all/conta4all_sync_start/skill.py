from __future__ import annotations
from service import Conta4allSyncStartService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return Conta4allSyncStartService().ejecutar(context)
