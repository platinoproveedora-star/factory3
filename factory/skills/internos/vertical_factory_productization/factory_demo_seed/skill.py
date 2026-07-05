from __future__ import annotations

from service import FactoryDemoSeedService


def run(context: dict) -> dict:
    return FactoryDemoSeedService().ejecutar(context or {})
