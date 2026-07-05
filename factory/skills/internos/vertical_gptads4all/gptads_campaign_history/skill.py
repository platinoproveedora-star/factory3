from __future__ import annotations

import importlib.util
from pathlib import Path


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    path = Path(__file__).parent / "service.py"
    spec = importlib.util.spec_from_file_location("gptads_campaign_history_svc", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.GptAdsCampaignHistoryService().ejecutar(context)
