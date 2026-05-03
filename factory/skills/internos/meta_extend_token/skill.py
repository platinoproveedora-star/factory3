"""Entrypoint for the portable meta_extend_token skill."""
from __future__ import annotations
from typing import Any
from service import MetaExtendTokenService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MetaExtendTokenService().ejecutar(context)
