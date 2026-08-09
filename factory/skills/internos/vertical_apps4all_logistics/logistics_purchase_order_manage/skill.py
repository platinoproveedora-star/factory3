from __future__ import annotations

from .service import LogisticsPurchaseOrderManageService


def run(context: dict) -> dict:
    return LogisticsPurchaseOrderManageService().ejecutar(context)
