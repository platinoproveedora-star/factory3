from __future__ import annotations

from service import IgCarouselImagePromptService


def run(context: dict) -> dict:
    return IgCarouselImagePromptService().ejecutar(context)
