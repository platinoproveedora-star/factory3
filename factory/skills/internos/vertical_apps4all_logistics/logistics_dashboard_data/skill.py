from __future__ import annotations

from service import LogisticsDashboardDataService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return LogisticsDashboardDataService().ejecutar(context)
