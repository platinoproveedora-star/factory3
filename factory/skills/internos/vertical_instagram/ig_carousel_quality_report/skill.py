from __future__ import annotations

from service import IgCarouselQualityReportService


def run(context: dict) -> dict:
    return IgCarouselQualityReportService().ejecutar(context)
