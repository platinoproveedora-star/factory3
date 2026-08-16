"""Motor de costeo PEPS (primeras entradas, primeras salidas). Igual que el
motor de cantidades, es un rebuild completo (no un parche incremental):
borra los lotes/consumo existentes de este producto+almacen+ambiente y
repasa TODOS sus movimientos en orden cronologico desde cero. Esto es
necesario porque el metodo PEPS depende del orden real de las compras — si
llega una compra retroactiva de un mes ya calculado, el orden de consumo de
lotes puede cambiar para TODAS las ventas posteriores, no solo las de ese
mes."""
from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


class InventoryCostRecalculateService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        product_id = str(context.get("product_id") or "").strip()
        warehouse_id = str(context.get("warehouse_id") or "").strip()
        environment = str(context.get("environment") or "sandbox").strip().lower()
        if not company_id or not product_id or not warehouse_id:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["company_id", "product_id", "warehouse_id"]}}

        dry_run = context.get("dry_run", True)
        db = SupabaseClient({**context, "schema": _SCHEMA})

        mv_res = db.rest_select(
            "cfdi_item_movements",
            filters={"company_id": f"eq.{company_id}", "product_id": f"eq.{product_id}", "warehouse_id": f"eq.{warehouse_id}", "environment": f"eq.{environment}"},
            select="id,movement_direction,quantity,unit_price,issued_at,cancels_movement_id",
            limit=5000,
        )
        if not mv_res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": mv_res.get("error")}}
        movements = [m for m in (mv_res.get("data") or []) if m.get("issued_at")]
        movements.sort(key=lambda m: m["issued_at"])

        lots: list[dict] = []
        consumption_by_movement: dict[str, list[dict]] = {}
        period_cost: dict[tuple[int, int], dict[str, float]] = {}
        warnings: list[str] = []

        for movement in movements:
            direction = movement["movement_direction"]
            quantity = float(movement.get("quantity") or 0)
            if quantity <= 0:
                continue
            year, month = int(movement["issued_at"][0:4]), int(movement["issued_at"][5:7])
            bucket = period_cost.setdefault((year, month), {"in_cost": 0.0, "out_cost": 0.0})

            if direction == "in":
                unit_cost = float(movement.get("unit_price") or 0)
                lots.append({
                    "source_movement_id": movement["id"], "unit_cost": unit_cost,
                    "quantity_in": quantity, "quantity_remaining": quantity,
                    "issued_at": movement["issued_at"], "consumptions": [],
                })
                bucket["in_cost"] += quantity * unit_cost

            elif direction == "out":
                to_consume = quantity
                consumed = []
                for lot in lots:
                    if to_consume <= 0:
                        break
                    if lot["quantity_remaining"] <= 0:
                        continue
                    take = min(lot["quantity_remaining"], to_consume)
                    lot["quantity_remaining"] -= take
                    lot["consumptions"].append({"quantity": take, "issued_at": movement["issued_at"]})
                    consumed.append({"lot": lot, "quantity": take, "unit_cost": lot["unit_cost"]})
                    to_consume -= take
                if to_consume > 0:
                    warnings.append(f"movimiento {movement['id']}: no hay suficiente costo historico para {to_consume} unidades — se valuo esa parte en $0 (venta sin compra respaldando)")
                consumption_by_movement[movement["id"]] = consumed
                bucket["out_cost"] += sum(c["quantity"] * c["unit_cost"] for c in consumed)

            elif direction == "out_cancelled":
                original_id = movement.get("cancels_movement_id")
                consumed = consumption_by_movement.get(original_id, [])
                total_cost = sum(c["quantity"] * c["unit_cost"] for c in consumed)
                total_qty = sum(c["quantity"] for c in consumed)
                avg_cost = round(total_cost / total_qty, 4) if total_qty else 0.0
                lots.append({
                    "source_movement_id": movement["id"], "unit_cost": avg_cost,
                    "quantity_in": quantity, "quantity_remaining": quantity,
                    "issued_at": movement["issued_at"], "consumptions": [],
                })
                bucket["out_cost"] -= quantity * avg_cost

        if dry_run:
            return {"ok": True, "message": "dry_run: costeo no escrito", "data": {"lots": len(lots), "warnings": warnings}}

        existing_lots = db.rest_select("inventory_cost_lots", filters={"company_id": f"eq.{company_id}", "product_id": f"eq.{product_id}", "warehouse_id": f"eq.{warehouse_id}", "environment": f"eq.{environment}"}, select="id")
        old_lot_ids = [row["id"] for row in (existing_lots.get("data") or [])]
        if old_lot_ids:
            db.rest_delete("inventory_lot_consumption", {"lot_id": f"in.({','.join(old_lot_ids)})"})
            db.rest_delete("inventory_cost_lots", {"company_id": f"eq.{company_id}", "product_id": f"eq.{product_id}", "warehouse_id": f"eq.{warehouse_id}", "environment": f"eq.{environment}"})

        for lot in lots:
            ins = db.rest_insert("inventory_cost_lots", {
                "company_id": company_id, "product_id": product_id, "warehouse_id": warehouse_id, "environment": environment,
                "source_movement_id": lot["source_movement_id"], "unit_cost": lot["unit_cost"],
                "quantity_in": lot["quantity_in"], "quantity_remaining": lot["quantity_remaining"], "issued_at": lot["issued_at"],
            })
            lot["_db_id"] = (ins.get("data") or [{}])[0].get("id") if ins.get("ok") else None

        for movement_id, consumed in consumption_by_movement.items():
            for entry in consumed:
                lot_db_id = entry["lot"].get("_db_id")
                if not lot_db_id:
                    continue
                db.rest_insert("inventory_lot_consumption", {
                    "lot_id": lot_db_id, "movement_id": movement_id, "quantity": entry["quantity"], "unit_cost": entry["unit_cost"],
                })

        periods_res = db.rest_select(
            "inventory_period_balance",
            filters={"company_id": f"eq.{company_id}", "product_id": f"eq.{product_id}", "warehouse_id": f"eq.{warehouse_id}", "environment": f"eq.{environment}"},
            select="id,year,month", limit=500,
        )
        updated_periods = []
        for period in (periods_res.get("data") or []):
            year, month = period["year"], period["month"]
            period_end = self._period_end(year, month)
            closing_value = 0.0
            for lot in lots:
                if lot["issued_at"] >= period_end:
                    continue
                consumed_by_then = sum(c["quantity"] for c in lot["consumptions"] if c["issued_at"] < period_end)
                remaining_by_then = lot["quantity_in"] - consumed_by_then
                closing_value += remaining_by_then * lot["unit_cost"]
            costs = period_cost.get((year, month), {"in_cost": 0.0, "out_cost": 0.0})
            values = {"in_cost": round(costs["in_cost"], 2), "out_cost": round(costs["out_cost"], 2), "closing_value": round(closing_value, 2)}
            db.rest_update("inventory_period_balance", values, {"id": f"eq.{period['id']}"})
            updated_periods.append({"year": year, "month": month, **values})

        return {"ok": True, "data": {"lots_created": len(lots), "periods_updated": updated_periods, "warnings": warnings}}

    def _period_end(self, year: int, month: int) -> str:
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        return f"{next_year:04d}-{next_month:02d}-01T00:00:00"
