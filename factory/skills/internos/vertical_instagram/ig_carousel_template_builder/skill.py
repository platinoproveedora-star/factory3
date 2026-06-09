from __future__ import annotations

from service import IgCarouselTemplateBuilderService


def run(context: dict) -> dict:
    return IgCarouselTemplateBuilderService().ejecutar(context)
