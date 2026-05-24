"""Entrypoint for rh_list_vacantes skill."""
from __future__ import annotations
from service import RhListVacantesService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhListVacantesService().ejecutar(context)
