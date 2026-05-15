from __future__ import annotations
from service import MetaLeadFormCreateService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return MetaLeadFormCreateService().ejecutar(context)
