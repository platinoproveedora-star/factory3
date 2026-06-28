from __future__ import annotations
from service import SecurityUserLoginService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return SecurityUserLoginService().ejecutar(context)
