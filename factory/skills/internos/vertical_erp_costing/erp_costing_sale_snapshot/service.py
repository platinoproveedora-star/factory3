from __future__ import annotations

from factory.engine import SupabaseClient


class ErpCostingSaleSnapshotService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        product_id = str(context.get("product_id") or "").strip()
        if not product_id:
            return {"ok": False, "error": "product_id requerido"}
        quantity = self._num(context.get("quantity"))
        if quantity <= 0:
            return {"ok": False, "error": "quantity debe ser mayor a cero"}
        requested_lot = self._blank(context.get("lot_code"))
        result = SupabaseClient(ctx).rest_select(
            "erp_kardex",
            filters={"product_id": product_id},
            select="*",
            order="created_at.desc",
            limit=10000,
        )
        if not result.get("ok"):
            return result
        lots, product = self._state(result.get("data") or [])
        active_lots = [lot for lot in lots if float(lot.get("quantity") or 0) > 0]
        if not active_lots:
            return {"ok": False, "error": "producto sin inventario disponible"}
        lot_code = requested_lot
        if not lot_code and len(active_lots) == 1:
            lot_code = active_lots[0]["lot_code"]
        if len(active_lots) > 1 and not lot_code:
            return {"ok": False, "error": "selecciona lote para este producto"}
        selected = next((lot for lot in active_lots if str(lot.get("lot_code")) == str(lot_code)), None)
        if not selected:
            return {"ok": False, "error": "lote invalido o sin saldo"}
        available = float(selected.get("quantity") or 0)
        if quantity > available:
            return {"ok": False, "error": f"lote {lot_code} no tiene saldo suficiente"}

        after_lots = []
        for lot in active_lots:
            qty = float(lot.get("quantity") or 0)
            if str(lot.get("lot_code")) == str(lot_code):
                qty -= quantity
            if qty > 0:
                after_lots.append({**lot, "quantity": qty})
        weighted_after = self._weighted_average(after_lots)
        weighted_before = float(product.get("weighted_avg_cost") or 0)
        lot_cost = float(selected.get("lot_unit_cost") or 0)
        last_cost = float(product.get("last_purchase_cost") or 0)
        return {
            "ok": True,
            "data": {
                "product_id": product_id,
                "lot_code": lot_code,
                "quantity": quantity,
                "available_quantity": round(available, 4),
                "lot_unit_cost": round(lot_cost, 4),
                "last_purchase_cost": round(last_cost, 4),
                "weighted_avg_cost": round(weighted_before, 4),
                "weighted_avg_cost_after_sale": round(weighted_after if after_lots else weighted_before, 4),
                "total_lot_cost": round(quantity * lot_cost, 4),
                "total_weighted_avg_cost": round(quantity * weighted_before, 4),
                "policy": "lot_last_weighted_average",
                "requires_lot": len(active_lots) > 1,
                "lots": active_lots,
            },
        }

    def _state(self, movements: list[dict]) -> tuple[list[dict], dict]:
        lots = {}
        last_purchase_cost = 0.0
        last_purchase_sort = ""
        for movement in movements:
            lot_code = self._lot_code(movement)
            lot = lots.setdefault(lot_code, {"lot_code": lot_code, "quantity": 0.0, "total_in": 0.0, "total_out": 0.0, "lot_unit_cost": 0.0, "last_movement_date": None})
            q_in = self._num(movement.get("quantity_in"))
            q_out = self._num(movement.get("quantity_out"))
            lot["quantity"] += q_in - q_out
            lot["total_in"] += q_in
            lot["total_out"] += q_out
            movement_date = movement.get("movement_date") or movement.get("created_at")
            if movement_date and (not lot["last_movement_date"] or str(movement_date) > str(lot["last_movement_date"])):
                lot["last_movement_date"] = movement_date
            if q_in > 0:
                unit_cost = self._movement_unit_cost(movement)
                if unit_cost or not lot["lot_unit_cost"]:
                    lot["lot_unit_cost"] = unit_cost
                sort_date = str(movement.get("created_at") or movement_date or "")
                if sort_date > last_purchase_sort:
                    last_purchase_sort = sort_date
                    last_purchase_cost = unit_cost
        rows = []
        for lot in lots.values():
            rows.append(
                {
                    **lot,
                    "quantity": round(float(lot.get("quantity") or 0), 4),
                    "total_in": round(float(lot.get("total_in") or 0), 4),
                    "total_out": round(float(lot.get("total_out") or 0), 4),
                    "lot_unit_cost": round(float(lot.get("lot_unit_cost") or 0), 4),
                    "inventory_value": round(float(lot.get("quantity") or 0) * float(lot.get("lot_unit_cost") or 0), 4),
                }
            )
        rows.sort(key=lambda row: (str(row.get("last_movement_date") or ""), str(row.get("lot_code") or "")))
        return rows, {"weighted_avg_cost": self._weighted_average(rows), "last_purchase_cost": last_purchase_cost}

    def _weighted_average(self, lots: list[dict]) -> float:
        qty = sum(float(lot.get("quantity") or 0) for lot in lots if float(lot.get("quantity") or 0) > 0)
        value = sum(float(lot.get("quantity") or 0) * float(lot.get("lot_unit_cost") or 0) for lot in lots if float(lot.get("quantity") or 0) > 0)
        return round(value / qty, 4) if qty > 0 else 0.0

    def _movement_unit_cost(self, movement: dict) -> float:
        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        for key in ("lot_unit_cost", "unit_cost", "last_purchase_cost"):
            if metadata.get(key) is not None:
                return self._num(metadata.get(key))
        return self._num(movement.get("unit_cost"))

    def _lot_code(self, movement: dict) -> str:
        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        value = movement.get("lot_code") or metadata.get("lot_code")
        value = str(value or "").strip()
        return value or "GENERAL"

    def _num(self, value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
