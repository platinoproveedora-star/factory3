from __future__ import annotations
from service import Gastos4AllCuentasRetiroSetupService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return Gastos4AllCuentasRetiroSetupService().ejecutar(context)
