from __future__ import annotations

from factory.engine import SupabaseClient


class ErpInventoryLotStockReportService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        db = SupabaseClient(ctx)
        products_res = db.rest_select("erp_products", select="*", order="product_name.asc", limit=10000)
        movements_res = db.rest_select("erp_kardex", select="*", order="created_at.desc", limit=10000)
        for result in (products_res, movements_res):
            if not result.get("ok"):
                return result
        products = {str(row.get("id")): row for row in products_res.get("data") or []}
        rows = self._lot_rows(products, movements_res.get("data") or [])
        return {
            "ok": True,
            "data": {
                "lots": rows,
                "summary": {
                    "lots": len(rows),
                    "active_lots": sum(1 for row in rows if float(row.get("quantity") or 0) > 0),
                    "estimated_value": round(sum(float(row.get("estimated_value") or 0) for row in rows), 2),
                },
            },
        }

    def _lot_rows(self, products: dict[str, dict], movements: list[dict]) -> list[dict]:
        by_lot = {}
        latest_cost = {}
        for movement in movements:
            product_id = str(movement.get("product_id") or "")
            if not product_id:
                continue
            lot_code = self._lot_code(movement)
            key = (product_id, lot_code)
            row = by_lot.setdefault(
                key,
                {"quantity": 0.0, "total_in": 0.0, "total_out": 0.0, "cost_qty": 0.0, "cost_amount": 0.0, "first_date": None, "last_date": None},
            )
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            row["quantity"] += q_in - q_out
            row["total_in"] += q_in
            row["total_out"] += q_out
            movement_date = movement.get("movement_date")
            if movement_date:
                row["first_date"] = movement_date if not row["first_date"] or str(movement_date) < str(row["first_date"]) else row["first_date"]
                row["last_date"] = movement_date if not row["last_date"] or str(movement_date) > str(row["last_date"]) else row["last_date"]
            if q_in > 0:
                unit_cost = float(movement.get("unit_cost") or 0)
                total_cost = float(movement.get("total_cost") or unit_cost * q_in)
                row["cost_qty"] += q_in
                row["cost_amount"] += total_cost
                if key not in latest_cost:
                    latest_cost[key] = unit_cost

        rows = []
        for (product_id, lot_code), stock in by_lot.items():
            product = products.get(product_id, {})
            qty = round(float(stock.get("quantity") or 0), 4)
            avg_cost = round(float(stock.get("cost_amount") or 0) / float(stock.get("cost_qty") or 1), 2) if float(stock.get("cost_qty") or 0) > 0 else 0.0
            rows.append(
                {
                    "product_id": product_id,
                    "lot_code": lot_code,
                    "display_name": f"{product.get('product_name') or 'Producto'} · {lot_code}",
                    "folio": product.get("folio"),
                    "product_key": product.get("product_key"),
                    "product_name": product.get("product_name"),
                    "sku": product.get("sku"),
                    "category": product.get("category"),
                    "category_2": product.get("category_2"),
                    "brand": product.get("brand"),
                    "unit": product.get("unit"),
                    "is_key_product": bool(product.get("is_key_product")),
                    "quantity": qty,
                    "total_in": round(float(stock.get("total_in") or 0), 4),
                    "total_out": round(float(stock.get("total_out") or 0), 4),
                    "avg_cost": avg_cost,
                    "last_cost": round(float(latest_cost.get((product_id, lot_code)) or 0), 2),
                    "estimated_value": round(qty * avg_cost, 2),
                    "first_movement_date": stock.get("first_date"),
                    "last_movement_date": stock.get("last_date"),
                }
            )
        return sorted(rows, key=lambda row: (not row.get("is_key_product"), str(row.get("product_name") or ""), str(row.get("lot_code") or "")))

    def _lot_code(self, movement: dict) -> str:
        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        value = movement.get("lot_code") or metadata.get("lot_code")
        value = str(value or "").strip()
        return value or "GENERAL"
