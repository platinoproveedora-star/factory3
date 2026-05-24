"""Entrypoint for new_supabase_table skill."""

from __future__ import annotations

from service import NewSupabaseTableService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return NewSupabaseTableService().ejecutar(context)
