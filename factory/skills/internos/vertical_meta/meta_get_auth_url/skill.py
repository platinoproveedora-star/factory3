"""Entrypoint for the portable meta_get_auth_url skill."""
from __future__ import annotations
from typing import Any
from service import MetaGetAuthUrlService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MetaGetAuthUrlService().ejecutar(context)
