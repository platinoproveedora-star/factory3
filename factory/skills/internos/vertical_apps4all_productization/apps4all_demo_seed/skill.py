from __future__ import annotations

from service import Apps4AllDemoSeedService


def run(context: dict) -> dict:
    return Apps4AllDemoSeedService().ejecutar(context or {})
