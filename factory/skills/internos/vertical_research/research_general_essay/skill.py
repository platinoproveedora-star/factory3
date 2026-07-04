from __future__ import annotations

from service import ResearchGeneralEssayService


def run(context: dict) -> dict:
    return ResearchGeneralEssayService().ejecutar(context)
