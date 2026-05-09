"""Entrypoint for ai_image_extractor skill."""

from __future__ import annotations

from service import AiImageExtractorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return AiImageExtractorService().ejecutar(context)
