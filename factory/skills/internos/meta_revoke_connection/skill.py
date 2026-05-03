"""Entrypoint for meta_revoke_connection skill."""
from __future__ import annotations

from typing import Any

from service import MetaRevokeConnectionService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MetaRevokeConnectionService().ejecutar(context)
