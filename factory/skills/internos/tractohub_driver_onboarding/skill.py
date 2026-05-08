"""Entrypoint for tractohub_driver_onboarding skill."""

from __future__ import annotations

from service import TractohubDriverOnboardingService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return TractohubDriverOnboardingService().ejecutar(context)
