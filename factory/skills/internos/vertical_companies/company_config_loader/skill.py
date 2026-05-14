from __future__ import annotations

from service import CompanyConfigLoaderService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return CompanyConfigLoaderService().ejecutar(context)
