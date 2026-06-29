from __future__ import annotations

import importlib.util
from pathlib import Path


def _common():
    path = Path(__file__).resolve().parents[1] / "_common.py"
    spec = importlib.util.spec_from_file_location("multi_shopper_common", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VerticalMultiShopperService:
    def ejecutar(self, context: dict) -> dict:
        action = context.get("action") or "health"
        if action == "schema_plan":
            schema = str(context.get("schema") or context.get("supabase_schema") or "").strip()
            if not schema:
                return {"ok": False, "error": "schema requerido en context"}
            return {"ok": True, "data": {"schema": schema, "sql": _common().schema_sql(schema)}}
        if action == "dashboard":
            return _common().MultiShopperDashboardDataService().ejecutar(context)
        return {
            "ok": True,
            "data": {
                "vertical": "vertical_multi_shopper",
                "commercial_name": "Purchasing IA Engine",
                "stage": "beta_1",
                "capabilities": [
                    "sales_quotes",
                    "products",
                    "suppliers",
                    "purchase_quotes",
                    "documents",
                    "price_history",
                    "erp_references_read_only",
                ],
                "forbidden_stage_1": [
                    "inventory_write",
                    "kardex_write",
                    "automatic_whatsapp_send",
                    "automatic_email_send",
                ],
            },
        }
