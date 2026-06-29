from __future__ import annotations

import importlib.util
from pathlib import Path


def _common():
    path = Path(__file__).resolve().parents[1] / "_common.py"
    spec = importlib.util.spec_from_file_location("multi_shopper_common", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PriceHistorySkillService:
    def ejecutar(self, context: dict) -> dict:
        if context.get("action") in {"update", "delete"}:
            return {"ok": False, "error": "price_history es append-only; no actualizar ni borrar"}
        return _common().MultiShopperCrudService("price_history").ejecutar(context)
