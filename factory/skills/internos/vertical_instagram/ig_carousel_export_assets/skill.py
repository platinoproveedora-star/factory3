from __future__ import annotations

from service import IgCarouselExportAssetsService


def run(context: dict) -> dict:
    return IgCarouselExportAssetsService().ejecutar(context)
