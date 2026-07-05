from __future__ import annotations

from service import Apps4AllDashScaffoldService


def run(context: dict) -> dict:
    return Apps4AllDashScaffoldService().ejecutar(context or {})
