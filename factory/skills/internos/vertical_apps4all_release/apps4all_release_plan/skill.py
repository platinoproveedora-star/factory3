from __future__ import annotations

from service import Apps4AllReleasePlanService


def run(context: dict) -> dict:
    return Apps4AllReleasePlanService().ejecutar(context or {})
