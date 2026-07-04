from __future__ import annotations

from service import ResearchTopicEssayService


def run(context: dict) -> dict:
    return ResearchTopicEssayService().ejecutar(context)
