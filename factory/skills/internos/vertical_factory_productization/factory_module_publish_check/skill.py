from __future__ import annotations

from service import FactoryModulePublishCheckService


def run(context: dict) -> dict:
    return FactoryModulePublishCheckService().ejecutar(context or {})
