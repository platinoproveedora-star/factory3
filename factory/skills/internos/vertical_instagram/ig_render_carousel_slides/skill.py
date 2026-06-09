from __future__ import annotations

from service import IgRenderCarouselSlidesService


def run(context: dict) -> dict:
    return IgRenderCarouselSlidesService().ejecutar(context)
