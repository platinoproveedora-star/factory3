from __future__ import annotations

import sys
from pathlib import Path

_LOGPLAT = Path(__file__).parent.parent.parent.parent.parent / "EMP_LOGPLAT"
if str(_LOGPLAT) not in sys.path:
    sys.path.insert(0, str(_LOGPLAT))


class LogplatRunService:

    def ejecutar(self, context: dict) -> dict:
        try:
            import bot_mode
            return {"ok": True, "data": bot_mode.ejecutar(
                context.get("update", {}),
                context.get("state", {}),
            )}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
