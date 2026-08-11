from __future__ import annotations
from service import WabizAccessCodeManageService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return WabizAccessCodeManageService().ejecutar(context)
