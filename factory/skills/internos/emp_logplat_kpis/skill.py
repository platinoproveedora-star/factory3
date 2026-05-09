"""Entrypoint for emp_logplat_kpis — kind=data KPI endpoint."""

from __future__ import annotations

from service import EmpLogplatKpisService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return EmpLogplatKpisService().ejecutar(context)
