def render(class_name: str) -> str:
    return f'''"""Runtime entrypoint for this portable skill."""

from __future__ import annotations

from typing import Any

from service import {class_name}Service


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {{"ok": False, "error": "context debe ser un diccionario"}}
    return {class_name}Service().ejecutar(context)
'''
