"""Entrypoint for markdown_table skill."""

from __future__ import annotations

from service import MarkdownTableService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MarkdownTableService().ejecutar(context)
