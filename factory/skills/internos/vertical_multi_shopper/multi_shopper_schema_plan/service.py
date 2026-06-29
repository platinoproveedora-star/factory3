from __future__ import annotations

import importlib.util
from pathlib import Path


def _common():
    path = Path(__file__).resolve().parents[1] / "_common.py"
    spec = importlib.util.spec_from_file_location("multi_shopper_common", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MultiShopperSchemaPlanService:
    def ejecutar(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema requerido en context"}
        return {"ok": True, "data": {"schema": schema, "sql": _common().schema_sql(schema)}}
