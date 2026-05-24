"""Entrypoint for supabase_insert_row skill."""

from __future__ import annotations

from service import SupabaseInsertRowService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SupabaseInsertRowService().ejecutar(context)
