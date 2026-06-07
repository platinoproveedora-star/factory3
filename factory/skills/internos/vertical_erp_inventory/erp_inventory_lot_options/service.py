from __future__ import annotations

from factory.engine import SupabaseClient


class ErpInventoryLotOptionsService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._schema_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        product_id = str(context.get("product_id") or "").strip()
        if not product_id:
            return {"ok": False, "error": "product_id requerido"}
        result = SupabaseClient(ctx).rest_select(
            "erp_kardex",
            filters={"product_id": product_id},
            select="*",
            order="created_at.desc",
            limit=10000,
        )
        if not result.get("ok"):
            return result
        data = self._costs(result.get("data") or [])
        return {"ok": True, "data": data}

    def _costs(self, movements: list[dict]) -> dict:
        lots = {}
        product_last_cost = 0.0
        product_last_sort = ""
        for movement in movements:
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            lot_code = self._lot_code(movement)
            lot = lots.setdefault(
                lot_code,
                {"quantity": 0.0, "total_in": 0.0, "total_out": 0.0, "lot_unit_cost": 0.0, "last_date": None},
            )
            lot["quantity"] += q_in - q_out
            lot["total_in"] += q_in
            lot["total_out"] += q_out
            movement_date = movement.get("movement_date") or movement.get("created_at")
            if movement_date and (not lot["last_date"] or str(movement_date) > str(lot["last_date"])):
                lot["last_date"] = movement_date
            if q_in > 0:
                unit_cost = self._movement_unit_cost(movement)
                if unit_cost or not lot["lot_unit_cost"]:
                    lot["lot_unit_cost"] = unit_cost
                sort_date = str(movement.get("created_at") or movement_date or "")
                if sort_date > product_last_sort:
                    product_last_sort = sort_date
                    product_last_cost = unit_cost

        active_qty = 0.0
        active_value = 0.0
        for lot in lots.values():
            qty = float(lot.get("quantity") or 0)
            if qty > 0:
                active_qty += qty
                active_value += qty * float(lot.get("lot_unit_cost") or 0)
        avg_cost = round(active_value / active_qty, 4) if active_qty > 0 else 0.0

        options = []
        for lot_code, lot in lots.items():
            qty = round(float(lot.get("quantity") or 0), 4)
            if qty <= 0:
                continue
            lot_cost = round(float(lot.get("lot_unit_cost") or 0), 4)
            options.append(
                {
                    "lot_code": lot_code,
                    "quantity": qty,
                    "total_in": round(float(lot.get("total_in") or 0), 4),
                    "total_out": round(float(lot.get("total_out") or 0), 4),
                    "lot_cost": lot_cost,
                    "lot_unit_cost": lot_cost,
                    "avg_cost": avg_cost,
                    "weighted_avg_cost": avg_cost,
                    "last_cost": round(product_last_cost, 4),
                    "last_purchase_cost": round(product_last_cost, 4),
                    "last_movement_date": lot.get("last_date"),
                    "label": f"{lot_code} - {qty:g} disp. - costo {lot_cost:.2f}",
                }
            )
        options.sort(key=lambda row: (str(row.get("last_movement_date") or ""), str(row.get("lot_code") or "")))
        return {
            "lots": options,
            "requires_lot": len(options) > 1,
            "default_lot_code": options[0]["lot_code"] if len(options) == 1 else None,
            "avg_cost": avg_cost,
            "weighted_avg_cost": avg_cost,
            "last_cost": round(product_last_cost, 4),
            "last_purchase_cost": round(product_last_cost, 4),
        }

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
