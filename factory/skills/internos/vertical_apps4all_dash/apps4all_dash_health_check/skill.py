from __future__ import annotations

from service import Apps4AllDashHealthCheckService


def run(context: dict) -> dict:
    return Apps4AllDashHealthCheckService().ejecutar(context or {})
