from __future__ import annotations

from service import Apps4AllFactoryBuildPlanService


def run(context: dict) -> dict:
    return Apps4AllFactoryBuildPlanService().ejecutar(context or {})
