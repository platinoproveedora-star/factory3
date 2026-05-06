"""Entrypoint for rh_vacante_store skill."""

from __future__ import annotations

from service import RhVacanteStoreService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhVacanteStoreService().ejecutar(context)
