from __future__ import annotations
from service import MetaAdsUpdateCampaignService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return MetaAdsUpdateCampaignService().ejecutar(context)
