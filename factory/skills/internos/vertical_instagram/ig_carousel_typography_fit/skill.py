from __future__ import annotations

from service import IgCarouselTypographyFitService


def run(context: dict) -> dict:
    return IgCarouselTypographyFitService().ejecutar(context)
