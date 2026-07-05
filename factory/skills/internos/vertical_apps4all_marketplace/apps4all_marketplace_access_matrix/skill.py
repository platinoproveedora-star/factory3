from __future__ import annotations

from service import Apps4AllMarketplaceAccessMatrixService


def run(context: dict) -> dict:
    return Apps4AllMarketplaceAccessMatrixService().ejecutar(context or {})
