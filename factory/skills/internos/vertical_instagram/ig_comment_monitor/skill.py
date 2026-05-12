from __future__ import annotations
from service import IgCommentMonitorService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return IgCommentMonitorService().ejecutar(context)
