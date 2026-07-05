from __future__ import annotations

from service import Apps4AllAuthBridgeHealthCheckService


def run(context: dict) -> dict:
    return Apps4AllAuthBridgeHealthCheckService().ejecutar(context or {})
