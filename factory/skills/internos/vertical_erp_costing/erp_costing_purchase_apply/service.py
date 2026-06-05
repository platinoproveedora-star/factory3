from __future__ import annotations


class ErpCostingPurchaseApplyService:
    def ejecutar(self, context: dict) -> dict:
        product_id = str(context.get("product_id") or "").strip()
        if not product_id:
            return {"ok": False, "error": "product_id requerido"}
        quantity = self._num(context.get("quantity"))
        unit_cost = self._num(context.get("unit_cost"))
        if quantity <= 0:
            return {"ok": False, "error": "quantity debe ser mayor a cero"}
        if unit_cost < 0:
            return {"ok": False, "error": "unit_cost no puede ser negativo"}
        tax_rate = self._num(context.get("tax_rate"))
        if tax_rate in {8.0, 16.0}:
            tax_rate = tax_rate / 100
        subtotal = round(quantity * unit_cost, 4)
        tax_amount = round(subtotal * tax_rate, 4)
        return {
            "ok": True,
            "data": {
                "product_id": product_id,
                "lot_code": self._blank(context.get("lot_code")) or "GENERAL",
                "quantity": quantity,
                "lot_unit_cost": round(unit_cost, 4),
                "last_purchase_cost": round(unit_cost, 4),
                "weighted_avg_cost": None,
                "cost_subtotal": subtotal,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "line_total": round(subtotal + tax_amount, 4),
                "policy": "lot_last_weighted_average",
            },
        }

    def _num(self, value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
