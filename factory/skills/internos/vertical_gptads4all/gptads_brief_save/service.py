from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gptads_library import save_brief, tenant_context  # noqa: E402


class GptAdsBriefSaveService:
    def ejecutar(self, context: dict) -> dict:
        ctx = tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        return save_brief(ctx["data"], context)
