from __future__ import annotations

from service import Apps4AllDeploySyncService


def run(context: dict) -> dict:
    return Apps4AllDeploySyncService().ejecutar(context or {})
