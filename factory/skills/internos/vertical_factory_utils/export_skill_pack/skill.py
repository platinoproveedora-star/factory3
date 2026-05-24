"""Entrypoint for export_skill_pack skill."""

from __future__ import annotations

from service import ExportSkillPackService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return ExportSkillPackService().ejecutar(context)
