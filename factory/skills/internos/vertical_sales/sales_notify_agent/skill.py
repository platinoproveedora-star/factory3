from __future__ import annotations
from service import SalesNotifyAgentService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return SalesNotifyAgentService().ejecutar(context)
