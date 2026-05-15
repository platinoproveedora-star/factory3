from __future__ import annotations

from service import CampaignLaunchPausedService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return CampaignLaunchPausedService().ejecutar(context)
