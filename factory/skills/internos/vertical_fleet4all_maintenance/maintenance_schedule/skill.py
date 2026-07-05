from __future__ import annotations

from service import MaintenanceScheduleService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return MaintenanceScheduleService().ejecutar(context)
