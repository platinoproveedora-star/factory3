from __future__ import annotations

from service import IgCarouselImageBriefService


def run(context: dict) -> dict:
    return IgCarouselImageBriefService().ejecutar(context)
