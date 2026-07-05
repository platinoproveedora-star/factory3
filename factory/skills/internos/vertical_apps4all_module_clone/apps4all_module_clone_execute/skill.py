from __future__ import annotations

from service import Apps4AllModuleCloneExecuteService


def run(context: dict) -> dict:
    return Apps4AllModuleCloneExecuteService().ejecutar(context or {})
