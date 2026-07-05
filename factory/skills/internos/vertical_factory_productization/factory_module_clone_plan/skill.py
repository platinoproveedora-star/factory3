from __future__ import annotations

from service import FactoryModuleClonePlanService


def run(context: dict) -> dict:
    return FactoryModuleClonePlanService().ejecutar(context or {})
