from __future__ import annotations

from service import ErpVentasRemisionCancelService


def run(context: dict) -> dict:
    return ErpVentasRemisionCancelService().ejecutar(context)
