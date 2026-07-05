from __future__ import annotations

from service import Apps4AllOpsMonitoringPlanService


def run(context: dict) -> dict:
    return Apps4AllOpsMonitoringPlanService().ejecutar(context or {})
