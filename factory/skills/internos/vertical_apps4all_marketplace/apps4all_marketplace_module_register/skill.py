from __future__ import annotations

from service import Apps4AllMarketplaceModuleRegisterService


def run(context: dict) -> dict:
    return Apps4AllMarketplaceModuleRegisterService().ejecutar(context or {})
