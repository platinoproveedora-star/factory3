from __future__ import annotations

from service import IgCarouselExportPngService


def run(context: dict) -> dict:
    return IgCarouselExportPngService().ejecutar(context)
