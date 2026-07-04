from __future__ import annotations

from service import IgCarouselAutofixDesignService


def run(context: dict) -> dict:
    return IgCarouselAutofixDesignService().ejecutar(context)
