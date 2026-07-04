from __future__ import annotations

from service import PurchaseImportSkillService


def run(context: dict) -> dict:
    return PurchaseImportSkillService().ejecutar(context)
