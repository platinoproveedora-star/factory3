from __future__ import annotations

from service import Apps4AllModuleClonePlanService


def run(context: dict) -> dict:
    return Apps4AllModuleClonePlanService().ejecutar(context or {})
