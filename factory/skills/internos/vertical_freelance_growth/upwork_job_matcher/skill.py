from __future__ import annotations
from service import UpworkJobMatcherService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return UpworkJobMatcherService().ejecutar(context)
