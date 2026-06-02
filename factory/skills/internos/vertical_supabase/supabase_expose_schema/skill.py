from __future__ import annotations
from service import SupabaseExposeSchemaService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return SupabaseExposeSchemaService().ejecutar(context)
