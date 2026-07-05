from __future__ import annotations

from service import QuotePdfSendService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return QuotePdfSendService().ejecutar(context)
