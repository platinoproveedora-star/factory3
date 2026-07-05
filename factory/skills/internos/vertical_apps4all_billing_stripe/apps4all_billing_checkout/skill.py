from __future__ import annotations

from service import Apps4AllBillingCheckoutService


def run(context: dict) -> dict:
    return Apps4AllBillingCheckoutService().ejecutar(context or {})
