from __future__ import annotations


class ErpInventoryStockReportService:
    def ejecutar(self, context: dict) -> dict:
        movements = context.get("movements") or context.get("kardex") or []
        products = {p.get("id"): p for p in context.get("products") or [] if isinstance(p, dict)}
        stock = {}
        for movement in movements:
            if not isinstance(movement, dict):
                continue
            product_id = movement.get("product_id")
            if not product_id:
                continue
            item = stock.setdefault(product_id, {"product_id": product_id, "quantity": 0.0, "total_in": 0.0, "total_out": 0.0})
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            item["total_in"] += q_in
            item["total_out"] += q_out
            item["quantity"] += q_in - q_out
        rows = []
        for product_id, item in stock.items():
            product = products.get(product_id, {})
            rows.append({**item, "product_name": product.get("product_name") or product.get("name") or product_id, "unit": product.get("unit")})
        rows.sort(key=lambda row: row["quantity"], reverse=True)
        return {"ok": True, "data": {"stock": rows, "top_5": rows[:5], "total_products": len(rows)}}

