from __future__ import annotations

import importlib.util
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]


class ErpVentasProductListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._inventory_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        result = SupabaseClient(ctx).rest_select(
            "erp_products",
            filters={"active": "eq.true"},
            select="id,folio,product_name,sku,unit,category,min_stock,weight_kg,weight_unit,weight_notes",
            order="product_name.asc",
        )
        if not result.get("ok"):
            return result
        products = result.get("data", []) or []
        return {"ok": True, "data": {"products": self._with_stock(ctx, products)}}

    def _with_stock(self, context: dict, products: list[dict]) -> list[dict]:
        stock_result = self._current_stock(context)
        if not stock_result.get("ok"):
            return products
        stock_rows = (stock_result.get("data") or {}).get("stock") or []
        by_product = {str(row.get("product_id") or ""): row for row in stock_rows if row.get("product_id")}
        enriched = []
        for product in products:
            stock = by_product.get(str(product.get("id") or ""), {})
            quantity = round(float(stock.get("quantity") or 0), 4)
            enriched.append(
                {
                    **product,
                    "quantity": quantity,
                    "current_stock": quantity,
                    "stock_status": stock.get("stock_status") or "ok",
                    "stock_delta": stock.get("stock_delta"),
                    "total_in": stock.get("total_in"),
                    "total_out": stock.get("total_out"),
                    "last_cost": stock.get("last_cost"),
                    "avg_cost": stock.get("avg_cost"),
                }
            )
        return enriched

    def _current_stock(self, context: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_inventory" / "erp_inventory_current_stock_report" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_current_stock_report_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_current_stock_report"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryCurrentStockReportService().ejecutar(context)

    def _inventory_context(self, context: dict) -> dict:
        schema = str(context.get("schema_inventario") or context.get("inventory_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_inventario/inventory_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
