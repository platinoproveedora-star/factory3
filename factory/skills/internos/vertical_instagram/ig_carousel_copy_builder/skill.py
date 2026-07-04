from __future__ import annotations

from service import IgCarouselCopyBuilderService


def run(context: dict) -> dict:
    return IgCarouselCopyBuilderService().ejecutar(context)
