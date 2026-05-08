"""Entrypoint for the portable new_dashboard skill."""

from __future__ import annotations
from typing import Any
from service import NewDashboardService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return NewDashboardService().ejecutar(context)
