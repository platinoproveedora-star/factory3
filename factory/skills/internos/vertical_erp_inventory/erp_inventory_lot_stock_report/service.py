from __future__ import annotations

from factory.engine import SupabaseClient


class ErpInventoryLotStockReportService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._schema_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
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
        lot_unit_cost = {}
        latest_product_cost = {}
        latest_product_sort = {}
        for movement in movements:
            product_id = str(movement.get("product_id") or "")
            if not product_id:
                continue
            lot_code = self._lot_code(movement)
            key = (product_id, lot_code)
            row = by_lot.setdefault(
                key,
                {"quantity": 0.0, "total_in": 0.0, "total_out": 0.0, "first_date": None, "last_date": None},
            )
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            row["quantity"] += q_in - q_out
            row["total_in"] += q_in
            row["total_out"] += q_out
            movement_date = movement.get("movement_date") or movement.get("created_at")
            if movement_date:
                row["first_date"] = movement_date if not row["first_date"] or str(movement_date) < str(row["first_date"]) else row["first_date"]
                row["last_date"] = movement_date if not row["last_date"] or str(movement_date) > str(row["last_date"]) else row["last_date"]
            if q_in > 0:
                unit_cost = self._movement_unit_cost(movement)
                if unit_cost or key not in lot_unit_cost:
                    lot_unit_cost[key] = unit_cost
                sort_date = str(movement.get("created_at") or movement_date or "")
                if sort_date > latest_product_sort.get(product_id, ""):
                    latest_product_sort[product_id] = sort_date
                    latest_product_cost[product_id] = unit_cost

        product_qty = {}
        product_value = {}
        for (product_id, lot_code), stock in by_lot.items():
            qty = float(stock.get("quantity") or 0)
            cost = float(lot_unit_cost.get((product_id, lot_code)) or 0)
            if qty > 0:
                product_qty[product_id] = product_qty.get(product_id, 0.0) + qty
                product_value[product_id] = product_value.get(product_id, 0.0) + qty * cost

        rows = []
        for (product_id, lot_code), stock in by_lot.items():
            product = products.get(product_id, {})
            qty = round(float(stock.get("quantity") or 0), 4)
            lot_cost = round(float(lot_unit_cost.get((product_id, lot_code)) or 0), 4)
            weighted_avg_cost = round(product_value.get(product_id, 0.0) / product_qty.get(product_id, 1.0), 4) if product_qty.get(product_id, 0.0) > 0 else 0.0
            rows.append(
                {
                    "product_id": product_id,
                    "lot_code": lot_code,
                    "display_name": f"{product.get('product_name') or 'Producto'} - {lot_code}",
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
                    "lot_unit_cost": lot_cost,
                    "avg_cost": weighted_avg_cost,
                    "weighted_avg_cost": weighted_avg_cost,
                    "last_cost": round(float(latest_product_cost.get(product_id) or 0), 4),
                    "last_purchase_cost": round(float(latest_product_cost.get(product_id) or 0), 4),
                    "estimated_value": round(qty * lot_cost, 2),
                    "first_movement_date": stock.get("first_date"),
                    "last_movement_date": stock.get("last_date"),
                }
            )
        return sorted(rows, key=lambda row: (not row.get("is_key_product"), str(row.get("product_name") or ""), str(row.get("lot_code") or "")))

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

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or context.get("inventory_schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema/supabase_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
