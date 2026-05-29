from __future__ import annotations
from service import VercelProjectCreateService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return VercelProjectCreateService().ejecutar(context)
