from __future__ import annotations

from service import Apps4AllCompanyProjectScaffoldService


def run(context: dict) -> dict:
    return Apps4AllCompanyProjectScaffoldService().ejecutar(context or {})
