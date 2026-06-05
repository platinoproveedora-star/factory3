from __future__ import annotations

from factory.engine import SupabaseClient


class ErpCostingInventoryValuationService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        filters = {}
        product_id = str(context.get("product_id") or "").strip()
        if product_id:
            filters["product_id"] = product_id
        result = SupabaseClient(ctx).rest_select("erp_kardex", filters=filters, select="*", order="created_at.desc", limit=10000)
        if not result.get("ok"):
            return result
        lots, products = self.valuate(result.get("data") or [])
        if product_id:
            lots = [row for row in lots if row.get("product_id") == product_id]
            products = [row for row in products if row.get("product_id") == product_id]
        return {
            "ok": True,
            "data": {
                "lots": lots,
                "products": products,
                "summary": {
                    "products": len(products),
                    "lots": len(lots),
                    "inventory_value": round(sum(float(row.get("inventory_value") or 0) for row in products), 2),
                },
            },
        }

    def valuate(self, movements: list[dict]) -> tuple[list[dict], list[dict]]:
        lots = {}
        last_purchase = {}
        for movement in movements:
            product_id = str(movement.get("product_id") or "")
            if not product_id:
                continue
            lot_code = self._lot_code(movement)
            key = (product_id, lot_code)
            lot = lots.setdefault(key, {"product_id": product_id, "lot_code": lot_code, "quantity": 0.0, "total_in": 0.0, "total_out": 0.0, "lot_unit_cost": 0.0, "first_date": None, "last_date": None})
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            lot["quantity"] += q_in - q_out
            lot["total_in"] += q_in
            lot["total_out"] += q_out
            movement_date = movement.get("movement_date") or movement.get("created_at")
            if movement_date:
                lot["first_date"] = movement_date if not lot["first_date"] or str(movement_date) < str(lot["first_date"]) else lot["first_date"]
                lot["last_date"] = movement_date if not lot["last_date"] or str(movement_date) > str(lot["last_date"]) else lot["last_date"]
            if q_in > 0:
                unit_cost = self._movement_unit_cost(movement)
                if unit_cost or not lot["lot_unit_cost"]:
                    lot["lot_unit_cost"] = unit_cost
                current_last = last_purchase.get(product_id)
                if not current_last or str(movement.get("created_at") or movement_date or "") > str(current_last.get("sort_date") or ""):
                    last_purchase[product_id] = {"cost": unit_cost, "sort_date": movement.get("created_at") or movement_date}

        product_acc = {}
        lot_rows = []
        for lot in lots.values():
            qty = round(float(lot.get("quantity") or 0), 4)
            unit_cost = round(float(lot.get("lot_unit_cost") or 0), 4)
            value = round(qty * unit_cost, 4)
            lot_row = {
                **lot,
                "quantity": qty,
                "total_in": round(float(lot.get("total_in") or 0), 4),
                "total_out": round(float(lot.get("total_out") or 0), 4),
                "lot_unit_cost": unit_cost,
                "inventory_value": value,
            }
            if qty > 0:
                lot_rows.append(lot_row)
            product = product_acc.setdefault(lot["product_id"], {"product_id": lot["product_id"], "quantity": 0.0, "inventory_value": 0.0, "lots": 0})
            if qty > 0:
                product["quantity"] += qty
                product["inventory_value"] += value
                product["lots"] += 1

        product_rows = []
        for product_id, product in product_acc.items():
            qty = float(product.get("quantity") or 0)
            value = float(product.get("inventory_value") or 0)
            product_rows.append(
                {
                    "product_id": product_id,
                    "quantity": round(qty, 4),
                    "inventory_value": round(value, 4),
                    "weighted_avg_cost": round(value / qty, 4) if qty > 0 else 0.0,
                    "last_purchase_cost": round(float((last_purchase.get(product_id) or {}).get("cost") or 0), 4),
                    "lots": product.get("lots") or 0,
                }
            )
        lot_rows.sort(key=lambda row: (str(row.get("product_id") or ""), str(row.get("lot_code") or "")))
        product_rows.sort(key=lambda row: str(row.get("product_id") or ""))
        return lot_rows, product_rows

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
