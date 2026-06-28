from __future__ import annotations
from service import SecuritySupportDecryptSessionService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return SecuritySupportDecryptSessionService().ejecutar(context)
