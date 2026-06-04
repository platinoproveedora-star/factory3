from __future__ import annotations

from service import RenderNextjsServiceDeployService


def run(context: dict) -> dict:
    return RenderNextjsServiceDeployService().ejecutar(context)
