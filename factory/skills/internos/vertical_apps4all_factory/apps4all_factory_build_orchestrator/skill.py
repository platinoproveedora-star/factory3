from __future__ import annotations

from service import Apps4AllFactoryBuildOrchestratorService


def run(context: dict) -> dict:
    return Apps4AllFactoryBuildOrchestratorService().ejecutar(context or {})
