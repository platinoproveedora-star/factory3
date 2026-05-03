"""Entrypoint for connect_supabase skill."""

from __future__ import annotations

from service import ConnectSupabaseService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return ConnectSupabaseService().ejecutar(context)
