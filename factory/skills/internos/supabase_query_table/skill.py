"""Entrypoint for supabase_query_table skill."""

from __future__ import annotations

from service import SupabaseQueryTableService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SupabaseQueryTableService().ejecutar(context)
