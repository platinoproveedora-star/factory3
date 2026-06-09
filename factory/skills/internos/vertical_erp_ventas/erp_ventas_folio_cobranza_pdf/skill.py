from __future__ import annotations

from service import ErpVentasFolioCobranzaPdfService


def run(context: dict) -> dict:
    return ErpVentasFolioCobranzaPdfService().ejecutar(context)
