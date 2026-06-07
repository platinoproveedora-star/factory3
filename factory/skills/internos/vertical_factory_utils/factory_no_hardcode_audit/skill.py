from __future__ import annotations

from service import FactoryNoHardcodeAuditService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return FactoryNoHardcodeAuditService().ejecutar(context)
