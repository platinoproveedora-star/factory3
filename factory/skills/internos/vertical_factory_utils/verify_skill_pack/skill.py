"""Entrypoint for verify_skill_pack skill."""

from __future__ import annotations

from service import VerifySkillPackService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return VerifySkillPackService().ejecutar(context)
