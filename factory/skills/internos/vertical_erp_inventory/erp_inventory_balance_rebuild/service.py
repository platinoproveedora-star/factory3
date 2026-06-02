from __future__ import annotations


class ErpInventoryBalanceRebuildService:
    def ejecutar(self, context: dict) -> dict:
        movements = [m for m in (context.get("movements") or []) if isinstance(m, dict)]
        movements.sort(key=lambda m: (m.get("product_id") or "", m.get("movement_date") or "", m.get("created_at") or "", m.get("folio") or ""))
        balances = {}
        rebuilt = []
        negatives = []
        for movement in movements:
            product_id = movement.get("product_id")
            if not product_id:
                continue
            balance = balances.get(product_id, 0.0)
            balance += float(movement.get("quantity_in") or 0) - float(movement.get("quantity_out") or 0)
            balances[product_id] = balance
            row = {**movement, "balance_after": balance}
            rebuilt.append(row)
            if balance < 0:
                negatives.append({"product_id": product_id, "folio": movement.get("folio"), "balance_after": balance})
        return {"ok": not negatives, "data": {"rebuilt": rebuilt, "balances": balances, "negatives": negatives}}

