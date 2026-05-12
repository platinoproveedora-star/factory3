"""Entrypoint for meta_refresh_connection skill."""
from __future__ import annotations

from typing import Any

from service import MetaRefreshConnectionService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MetaRefreshConnectionService().ejecutar(context)
