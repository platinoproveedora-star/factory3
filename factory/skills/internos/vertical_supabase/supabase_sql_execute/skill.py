"""Entrypoint for supabase_sql_execute skill."""

from __future__ import annotations

from service import SupabaseSqlExecuteService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SupabaseSqlExecuteService().ejecutar(context)
