"""Entrypoint for add_agent_memory_supabase skill."""

from __future__ import annotations

from service import AddAgentMemorySupabaseService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return AddAgentMemorySupabaseService().ejecutar(context)
