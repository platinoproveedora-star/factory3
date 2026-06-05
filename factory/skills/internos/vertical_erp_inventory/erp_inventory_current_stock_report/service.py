from __future__ import annotations

from factory.engine import SupabaseClient


class ErpInventoryCurrentStockReportService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        db = SupabaseClient(ctx)
        products_res = db.rest_select("erp_products", select="*", order="product_name.asc", limit=10000)
        movements_res = db.rest_select("erp_kardex", select="*", order="created_at.desc", limit=10000)
        for result in (products_res, movements_res):
            if not result.get("ok"):
                return result
        rows = self._stock(products_res.get("data") or [], movements_res.get("data") or [])
        return {
            "ok": True,
            "data": {
                "stock": rows,
                "key_products": [row for row in rows if row.get("is_key_product")],
                "summary": {
                    "products": len(rows),
                    "key_products": sum(1 for row in rows if row.get("is_key_product")),
                    "low_stock": sum(1 for row in rows if row.get("stock_status") == "bajo"),
                    "negative_stock": sum(1 for row in rows if row.get("stock_status") == "negativo"),
                    "estimated_value": round(sum(float(row.get("estimated_value") or 0) for row in rows), 2),
                },
            },
        }

    def _stock(self, products: list[dict], movements: list[dict]) -> list[dict]:
        by_product = {}
        latest_cost = {}
        lot_state = {}
        for movement in movements:
            product_id = movement.get("product_id")
            if not product_id:
                continue
            row = by_product.setdefault(product_id, {"quantity": 0.0, "total_in": 0.0, "total_out": 0.0})
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            lot_code = self._lot_code(movement)
            lot_key = (product_id, lot_code)
            lot = lot_state.setdefault(lot_key, {"quantity": 0.0, "lot_unit_cost": 0.0})
            lot["quantity"] += q_in - q_out
            row["quantity"] += q_in - q_out
            row["total_in"] += q_in
            row["total_out"] += q_out
            if q_in > 0:
                unit_cost = self._movement_unit_cost(movement)
                if unit_cost or not lot["lot_unit_cost"]:
                    lot["lot_unit_cost"] = unit_cost
                if product_id not in latest_cost:
                    latest_cost[product_id] = unit_cost

        weighted = {}
        for (product_id, _lot_code), lot in lot_state.items():
            qty = float(lot.get("quantity") or 0)
            if qty <= 0:
                continue
            product = weighted.setdefault(product_id, {"quantity": 0.0, "value": 0.0})
            product["quantity"] += qty
            product["value"] += qty * float(lot.get("lot_unit_cost") or 0)

        rows = []
        for product in products:
            product_id = product.get("id")
            stock = by_product.get(product_id, {"quantity": 0.0, "total_in": 0.0, "total_out": 0.0})
            qty = round(float(stock.get("quantity") or 0), 4)
            min_stock = float(product.get("min_stock") or 0)
            weighted_row = weighted.get(product_id, {})
            avg_cost = round(float(weighted_row.get("value") or 0) / float(weighted_row.get("quantity") or 1), 4) if float(weighted_row.get("quantity") or 0) > 0 else 0.0
            status = "negativo" if qty < 0 else "bajo" if min_stock and qty < min_stock else "ok"
            rows.append(
                {
                    "product_id": product_id,
                    "folio": product.get("folio"),
                    "product_key": product.get("product_key"),
                    "product_name": product.get("product_name"),
                    "sku": product.get("sku"),
                    "category": product.get("category"),
                    "category_2": product.get("category_2"),
                    "brand": product.get("brand"),
                    "unit": product.get("unit"),
                    "active": product.get("active") is not False,
                    "is_key_product": bool(product.get("is_key_product")),
                    "min_stock": min_stock,
                    "quantity": qty,
                    "total_in": round(float(stock.get("total_in") or 0), 4),
                    "total_out": round(float(stock.get("total_out") or 0), 4),
                    "stock_delta": round(qty - min_stock, 4),
                    "stock_status": status,
                    "avg_cost": avg_cost,
                    "weighted_avg_cost": avg_cost,
                    "last_cost": round(float(latest_cost.get(product_id) or 0), 4),
                    "last_purchase_cost": round(float(latest_cost.get(product_id) or 0), 4),
                    "estimated_value": round(qty * avg_cost, 2),
                }
            )
        return sorted(rows, key=lambda row: (not row.get("is_key_product"), str(row.get("product_name") or "")))

    def _movement_unit_cost(self, movement: dict) -> float:
        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        for key in ("lot_unit_cost", "unit_cost", "last_purchase_cost"):
            if metadata.get(key) is not None:
                try:
                    return float(metadata.get(key) or 0)
                except (TypeError, ValueError):
                    pass
        return float(movement.get("unit_cost") or 0)

    def _lot_code(self, movement: dict) -> str:
        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        value = movement.get("lot_code") or metadata.get("lot_code")
        value = str(value or "").strip()
        return value or "GENERAL"
