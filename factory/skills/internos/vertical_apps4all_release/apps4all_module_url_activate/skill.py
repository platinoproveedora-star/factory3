from __future__ import annotations

from service import Apps4AllModuleUrlActivateService


def run(context: dict) -> dict:
    return Apps4AllModuleUrlActivateService().ejecutar(context or {})
