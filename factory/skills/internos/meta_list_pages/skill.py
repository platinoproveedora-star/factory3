"""Runtime entrypoint for meta_list_pages."""
from __future__ import annotations

from typing import Any

from service import MetaListPagesService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return MetaListPagesService().ejecutar(context)
