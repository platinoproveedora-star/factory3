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
        products = products_res.get("data") or []
        movements = movements_res.get("data") or []
        rows = self._stock(products, movements)
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
        for movement in movements:
            product_id = movement.get("product_id")
            if not product_id:
                continue
            row = by_product.setdefault(product_id, {"quantity": 0.0, "total_in": 0.0, "total_out": 0.0, "cost_qty": 0.0, "cost_amount": 0.0})
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            row["quantity"] += q_in - q_out
            row["total_in"] += q_in
            row["total_out"] += q_out
            if q_in > 0:
                unit_cost = float(movement.get("unit_cost") or 0)
                total_cost = float(movement.get("total_cost") or unit_cost * q_in)
                row["cost_qty"] += q_in
                row["cost_amount"] += total_cost
                if product_id not in latest_cost:
                    latest_cost[product_id] = unit_cost

        rows = []
        for product in products:
            product_id = product.get("id")
            stock = by_product.get(product_id, {"quantity": 0.0, "total_in": 0.0, "total_out": 0.0, "cost_qty": 0.0, "cost_amount": 0.0})
            qty = round(float(stock.get("quantity") or 0), 4)
            min_stock = float(product.get("min_stock") or 0)
            avg_cost = round(float(stock.get("cost_amount") or 0) / float(stock.get("cost_qty") or 1), 2) if float(stock.get("cost_qty") or 0) > 0 else 0.0
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
                    "last_cost": round(float(latest_cost.get(product_id) or 0), 2),
                    "estimated_value": round(qty * avg_cost, 2),
                }
            )
        return sorted(rows, key=lambda row: (not row.get("is_key_product"), str(row.get("product_name") or "")))
