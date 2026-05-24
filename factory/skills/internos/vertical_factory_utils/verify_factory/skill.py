"""Entrypoint for the portable verify_factory skill."""

from __future__ import annotations

from typing import Any

from service import VerifyFactoryService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return VerifyFactoryService().ejecutar(context)
