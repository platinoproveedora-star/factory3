"""Entrypoint for the portable security_gate skill."""

from __future__ import annotations

from typing import Any

from service import SecurityGateService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "verdict": "FAIL", "error": "context debe ser un diccionario"}
    return SecurityGateService().ejecutar(context)
