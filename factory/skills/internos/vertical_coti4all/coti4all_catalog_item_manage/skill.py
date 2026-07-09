from __future__ import annotations
from service import Coti4AllCatalogItemManageService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return Coti4AllCatalogItemManageService().ejecutar(context)
