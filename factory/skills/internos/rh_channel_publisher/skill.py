"""Entrypoint for the portable rh_channel_publisher skill."""

from __future__ import annotations
from typing import Any
from service import RhChannelPublisherService


def run(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return RhChannelPublisherService().ejecutar(context)
