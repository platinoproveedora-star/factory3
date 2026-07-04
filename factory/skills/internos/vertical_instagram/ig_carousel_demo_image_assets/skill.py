from __future__ import annotations

from service import IgCarouselDemoImageAssetsService


def run(context: dict) -> dict:
    return IgCarouselDemoImageAssetsService().ejecutar(context)
