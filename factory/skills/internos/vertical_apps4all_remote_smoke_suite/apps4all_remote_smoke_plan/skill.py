from __future__ import annotations

from service import Apps4AllRemoteSmokePlanService


def run(context: dict) -> dict:
    return Apps4AllRemoteSmokePlanService().ejecutar(context or {})
