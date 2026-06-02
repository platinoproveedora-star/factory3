from __future__ import annotations

from service import ErpInventoryPartySaveService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return ErpInventoryPartySaveService().ejecutar(context)
