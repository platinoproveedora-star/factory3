from __future__ import annotations
from service import WabizSendMediaService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return WabizSendMediaService().ejecutar(context)
