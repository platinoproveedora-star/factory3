from __future__ import annotations

from service import Apps4AllPublishCheckService


def run(context: dict) -> dict:
    return Apps4AllPublishCheckService().ejecutar(context or {})
