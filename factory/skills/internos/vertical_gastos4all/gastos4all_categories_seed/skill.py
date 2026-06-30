from __future__ import annotations
from service import Gastos4AllCategoriesSeedService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return Gastos4AllCategoriesSeedService().ejecutar(context)
