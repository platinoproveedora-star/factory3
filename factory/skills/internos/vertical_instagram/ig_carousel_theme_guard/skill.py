from __future__ import annotations

from service import IgCarouselThemeGuardService


def run(context: dict) -> dict:
    return IgCarouselThemeGuardService().ejecutar(context)
