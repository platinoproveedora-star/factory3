"""Entrypoint for rh_questionnaire_generator skill."""

from __future__ import annotations

from service import RhQuestionnaireGeneratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhQuestionnaireGeneratorService().ejecutar(context)
