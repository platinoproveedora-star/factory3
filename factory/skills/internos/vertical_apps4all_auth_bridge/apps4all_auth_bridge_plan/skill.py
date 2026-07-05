from __future__ import annotations

from service import Apps4AllAuthBridgePlanService


def run(context: dict) -> dict:
    return Apps4AllAuthBridgePlanService().ejecutar(context or {})
