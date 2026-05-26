from __future__ import annotations
from service import UpworkCaseStudyGeneratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return UpworkCaseStudyGeneratorService().ejecutar(context)
