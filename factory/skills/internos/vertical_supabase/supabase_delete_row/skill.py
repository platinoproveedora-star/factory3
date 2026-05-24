"""Entrypoint for supabase_delete_row skill."""

from __future__ import annotations

from service import SupabaseDeleteRowService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SupabaseDeleteRowService().ejecutar(context)
