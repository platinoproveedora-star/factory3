from __future__ import annotations
from service import DashboardUpdatePlannerService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return DashboardUpdatePlannerService().ejecutar(context)

