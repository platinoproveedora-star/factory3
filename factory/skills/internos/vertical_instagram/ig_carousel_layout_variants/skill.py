from __future__ import annotations

from service import IgCarouselLayoutVariantsService


def run(context: dict) -> dict:
    return IgCarouselLayoutVariantsService().ejecutar(context)
