from __future__ import annotations

from service import Apps4AllMarketplaceModuleListService


def run(context: dict) -> dict:
    return Apps4AllMarketplaceModuleListService().ejecutar(context or {})
