"""Entrypoint for money_parser skill."""

from __future__ import annotations

from service import MoneyParserService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MoneyParserService().ejecutar(context)
