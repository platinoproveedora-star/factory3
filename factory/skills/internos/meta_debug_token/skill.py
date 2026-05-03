"""Runtime entrypoint for meta_debug_token."""
from __future__ import annotations

from typing import Any

from service import MetaDebugTokenService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MetaDebugTokenService().ejecutar(context)
