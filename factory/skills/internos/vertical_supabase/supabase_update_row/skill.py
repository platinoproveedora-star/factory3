"""Entrypoint for supabase_update_row skill."""

from __future__ import annotations

from service import SupabaseUpdateRowService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SupabaseUpdateRowService().ejecutar(context)
