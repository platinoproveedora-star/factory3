from __future__ import annotations

from factory.engine import SupabaseClient


class ErpInventoryLotOptionsService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
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
        movements = result.get("data") or []
        data = self._costs(movements)
        return {"ok": True, "data": data}

    def _costs(self, movements: list[dict]) -> dict:
        lots = {}
        product_cost_qty = 0.0
        product_cost_amount = 0.0
        product_last_cost = 0.0
        for movement in movements:
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            lot_code = self._lot_code(movement)
            lot = lots.setdefault(lot_code, {"quantity": 0.0, "total_in": 0.0, "total_out": 0.0, "cost_qty": 0.0, "cost_amount": 0.0, "last_cost": 0.0, "last_date": None})
            lot["quantity"] += q_in - q_out
            lot["total_in"] += q_in
            lot["total_out"] += q_out
            movement_date = movement.get("movement_date")
            if movement_date and (not lot["last_date"] or str(movement_date) > str(lot["last_date"])):
                lot["last_date"] = movement_date
            if q_in > 0:
                unit_cost = float(movement.get("unit_cost") or 0)
                total_cost = float(movement.get("total_cost") or unit_cost * q_in)
                lot["cost_qty"] += q_in
                lot["cost_amount"] += total_cost
                if not lot["last_cost"]:
                    lot["last_cost"] = unit_cost
                product_cost_qty += q_in
                product_cost_amount += total_cost
                if not product_last_cost:
                    product_last_cost = unit_cost

        avg_cost = round(product_cost_amount / product_cost_qty, 2) if product_cost_qty > 0 else 0.0
        options = []
        for lot_code, lot in lots.items():
            qty = round(float(lot.get("quantity") or 0), 4)
            if qty <= 0:
                continue
            lot_avg_cost = round(float(lot.get("cost_amount") or 0) / float(lot.get("cost_qty") or 1), 2) if float(lot.get("cost_qty") or 0) > 0 else 0.0
            options.append(
                {
                    "lot_code": lot_code,
                    "quantity": qty,
                    "total_in": round(float(lot.get("total_in") or 0), 4),
                    "total_out": round(float(lot.get("total_out") or 0), 4),
                    "lot_cost": lot_avg_cost,
                    "avg_cost": avg_cost,
                    "last_cost": round(product_last_cost, 2),
                    "lot_last_cost": round(float(lot.get("last_cost") or 0), 2),
                    "last_movement_date": lot.get("last_date"),
                    "label": f"{lot_code} · {qty:g} disp. · costo {lot_avg_cost:.2f}",
                }
            )
        options.sort(key=lambda row: (str(row.get("last_movement_date") or ""), str(row.get("lot_code") or "")))
        return {
            "lots": options,
            "requires_lot": len(options) > 1,
            "default_lot_code": options[0]["lot_code"] if len(options) == 1 else None,
            "avg_cost": avg_cost,
            "last_cost": round(product_last_cost, 2),
        }

    def _lot_code(self, movement: dict) -> str:
        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        value = movement.get("lot_code") or metadata.get("lot_code")
        value = str(value or "").strip()
        return value or "GENERAL"
