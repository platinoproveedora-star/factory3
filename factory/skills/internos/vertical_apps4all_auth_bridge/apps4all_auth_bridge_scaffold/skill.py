from __future__ import annotations

from service import Apps4AllAuthBridgeScaffoldService


def run(context: dict) -> dict:
    return Apps4AllAuthBridgeScaffoldService().ejecutar(context or {})
