from __future__ import annotations
from service import VercelEnvSyncService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return VercelEnvSyncService().ejecutar(context)
