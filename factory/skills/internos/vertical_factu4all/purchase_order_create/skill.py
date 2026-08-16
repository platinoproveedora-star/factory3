from __future__ import annotations

from service import PurchaseOrderCreateService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return PurchaseOrderCreateService().ejecutar(context)
