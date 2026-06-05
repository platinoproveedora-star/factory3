from __future__ import annotations

import importlib.util
from pathlib import Path


class ErpCostingWeightedAverageRebuildService:
    def ejecutar(self, context: dict) -> dict:
        service_path = Path(__file__).resolve().parents[1] / "erp_costing_inventory_valuation" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_costing_inventory_valuation_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_costing_inventory_valuation"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.ErpCostingInventoryValuationService().ejecutar(context)
        if not result.get("ok"):
            return result
        products = result.get("data", {}).get("products") or []
        return {
            "ok": True,
            "data": {
                "products": [
                    {
                        "product_id": row.get("product_id"),
                        "quantity": row.get("quantity"),
                        "weighted_avg_cost": row.get("weighted_avg_cost"),
                        "last_purchase_cost": row.get("last_purchase_cost"),
                        "inventory_value": row.get("inventory_value"),
                    }
                    for row in products
                ],
                "dry_run": context.get("dry_run", True),
                "message": "rebuild calculado desde kardex; no escribe saldos fisicos",
            },
        }
