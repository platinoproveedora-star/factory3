from __future__ import annotations

from service import Apps4AllBillingPlanService


def run(context: dict) -> dict:
    return Apps4AllBillingPlanService().ejecutar(context or {})
