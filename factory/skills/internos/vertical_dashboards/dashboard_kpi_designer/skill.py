from __future__ import annotations
from service import DashboardKpiDesignerService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return DashboardKpiDesignerService().ejecutar(context)

