"""Runtime entrypoint for meta_get_instagram_account."""
from __future__ import annotations

from typing import Any

from service import MetaGetInstagramAccountService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MetaGetInstagramAccountService().ejecutar(context)
