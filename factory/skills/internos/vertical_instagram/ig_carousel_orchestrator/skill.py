from __future__ import annotations

from service import IgCarouselOrchestratorService


def run(context: dict) -> dict:
    return IgCarouselOrchestratorService().ejecutar(context)
