from __future__ import annotations

from service import CompanyScaffoldService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return CompanyScaffoldService().ejecutar(context)
