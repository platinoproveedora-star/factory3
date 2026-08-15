from __future__ import annotations

from service import DocumentDownloadService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return DocumentDownloadService().ejecutar(context)
