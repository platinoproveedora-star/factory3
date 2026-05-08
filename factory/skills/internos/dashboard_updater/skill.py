"""Entrypoint for the portable dashboard_updater skill."""

from __future__ import annotations
from typing import Any
from service import DashboardUpdaterService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return DashboardUpdaterService().ejecutar(context)
