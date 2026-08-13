from __future__ import annotations

from service import Factu4AllSchemaSetupService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return Factu4AllSchemaSetupService().ejecutar(context)
