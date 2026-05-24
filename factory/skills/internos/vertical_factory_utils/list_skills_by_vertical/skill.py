"""Entrypoint for list_skills_by_vertical skill."""

from __future__ import annotations

from service import ListSkillsByVerticalService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return ListSkillsByVerticalService().ejecutar(context)
