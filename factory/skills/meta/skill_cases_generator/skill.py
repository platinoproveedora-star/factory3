from __future__ import annotations
from service import SkillCasesGeneratorService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return SkillCasesGeneratorService().ejecutar(context)
