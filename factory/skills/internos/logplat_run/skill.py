"""Entrypoint for logplat_run — delegates to EMP_LOGPLAT/bot_mode.py."""

from __future__ import annotations

import sys
from pathlib import Path

_LOGPLAT = Path(__file__).parent.parent.parent.parent.parent / "EMP_LOGPLAT"
if str(_LOGPLAT) not in sys.path:
    sys.path.insert(0, str(_LOGPLAT))


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    try:
        import bot_mode
        return {"ok": True, "data": bot_mode.ejecutar(
            context.get("update", {}),
            context.get("state", {}),
        )}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
