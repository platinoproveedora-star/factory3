"""Entrypoint for new_factory_cloud skill."""

from __future__ import annotations

from service import NewFactoryCloudService


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser un diccionario"}
    return NewFactoryCloudService().ejecutar(context)
