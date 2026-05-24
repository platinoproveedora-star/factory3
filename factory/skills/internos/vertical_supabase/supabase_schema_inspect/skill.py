"""Entrypoint for supabase_schema_inspect skill."""

from __future__ import annotations

from service import SupabaseSchemaInspectService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SupabaseSchemaInspectService().ejecutar(context)
