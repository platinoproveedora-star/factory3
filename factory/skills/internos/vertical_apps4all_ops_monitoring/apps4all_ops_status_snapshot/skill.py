from __future__ import annotations

from service import Apps4AllOpsStatusSnapshotService


def run(context: dict) -> dict:
    return Apps4AllOpsStatusSnapshotService().ejecutar(context or {})
