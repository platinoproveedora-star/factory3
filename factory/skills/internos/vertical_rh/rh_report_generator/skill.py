"""Entrypoint for rh_report_generator skill."""

from __future__ import annotations

from service import RhReportGeneratorService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhReportGeneratorService().ejecutar(context)
