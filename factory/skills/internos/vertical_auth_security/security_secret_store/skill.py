from __future__ import annotations
from service import SecuritySecretStoreService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return SecuritySecretStoreService().ejecutar(context)
