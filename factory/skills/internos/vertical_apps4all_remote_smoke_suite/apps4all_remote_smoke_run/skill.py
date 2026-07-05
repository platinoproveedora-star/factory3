from __future__ import annotations

from service import Apps4AllRemoteSmokeRunService


def run(context: dict) -> dict:
    return Apps4AllRemoteSmokeRunService().ejecutar(context or {})
