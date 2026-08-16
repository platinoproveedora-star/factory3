from __future__ import annotations
from service import SatProdservClassifyService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return SatProdservClassifyService().ejecutar(context)
