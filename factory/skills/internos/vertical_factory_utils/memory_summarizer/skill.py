"""Entrypoint for memory_summarizer skill."""

from __future__ import annotations

from service import MemorySummarizerService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MemorySummarizerService().ejecutar(context)
