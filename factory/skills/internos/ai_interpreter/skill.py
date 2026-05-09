from __future__ import annotations

import service as svc


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return svc.run(context)
