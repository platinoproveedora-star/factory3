from __future__ import annotations
from service import QARollbackCampaignService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return QARollbackCampaignService().ejecutar(context)
