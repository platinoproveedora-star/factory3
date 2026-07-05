from __future__ import annotations

from service import Apps4AllMarketplaceModuleActivateService


def run(context: dict) -> dict:
    return Apps4AllMarketplaceModuleActivateService().ejecutar(context or {})
