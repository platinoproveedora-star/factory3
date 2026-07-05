from __future__ import annotations

from service import Apps4AllBillingStatusService


def run(context: dict) -> dict:
    return Apps4AllBillingStatusService().ejecutar(context or {})
