from __future__ import annotations

from service import Apps4AllMarketplaceSchemaSetupService


def run(context: dict) -> dict:
    return Apps4AllMarketplaceSchemaSetupService().ejecutar(context or {})
