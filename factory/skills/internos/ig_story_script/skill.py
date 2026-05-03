"""Entrypoint for the portable ig_story_script skill."""
from __future__ import annotations
from typing import Any
from service import IgStoryScriptService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return IgStoryScriptService().ejecutar(context)
