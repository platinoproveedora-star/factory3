from __future__ import annotations

from service import ExpenseManageService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return ExpenseManageService().ejecutar(context)
