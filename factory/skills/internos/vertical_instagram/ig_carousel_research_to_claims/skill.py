from __future__ import annotations

from service import IgCarouselResearchToClaimsService


def run(context: dict) -> dict:
    return IgCarouselResearchToClaimsService().ejecutar(context)
