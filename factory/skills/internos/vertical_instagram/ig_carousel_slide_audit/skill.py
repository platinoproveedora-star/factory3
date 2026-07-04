from __future__ import annotations

from service import IgCarouselSlideAuditService


def run(context: dict) -> dict:
    return IgCarouselSlideAuditService().ejecutar(context)
