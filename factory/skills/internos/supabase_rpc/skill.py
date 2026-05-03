"""Entrypoint for supabase_rpc skill."""

from __future__ import annotations

from service import SupabaseRpcService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return SupabaseRpcService().ejecutar(context)
