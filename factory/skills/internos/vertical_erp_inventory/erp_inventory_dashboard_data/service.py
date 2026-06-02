from __future__ import annotations

from datetime import date, datetime


KEY_RULES = [
    {"product_key": "varilla_3_8", "product_name": "Varilla 3/8", "threshold_days": 7, "alert_frequency": "daily"},
    {"product_key": "varilla_1_2", "product_name": "Varilla 1/2", "threshold_days": 7, "alert_frequency": "daily"},
    {"product_key": "cemento", "product_name": "Cemento", "threshold_days": 7, "alert_frequency": "daily"},
]


class ErpInventoryDashboardDataService:
    def ejecutar(self, context: dict) -> dict:
        action = str(context.get("action") or "summary").strip()
        movements = [m for m in (context.get("movements") or context.get("kardex") or []) if isinstance(m, dict)]
        products = [p for p in (context.get("products") or []) if isinstance(p, dict)]
        parties = [p for p in (context.get("parties") or []) if isinstance(p, dict)]

        if action == "summary":
            return {"ok": True, "data": self._summary(movements, products, parties)}
        if action == "receivables":
            return {"ok": True, "data": {"receivables": self._receivables(movements)}}
        if action == "sales_by_product_month":
            return {"ok": True, "data": {"sales_by_product_month": self._sales_by_product_month(movements, products, context)}}
        if action == "top_inventory":
            return {"ok": True, "data": {"top_inventory": self._stock(movements, products)[:5]}}
        if action == "recurrence_alerts":
            return {"ok": True, "data": {"recurrence_alerts": self._recurrence_alerts(movements, products, parties, context)}}
        if action == "last_purchase_by_customer":
            return {"ok": True, "data": {"last_purchase_by_customer": self._last_purchase_by_customer(movements, products, parties)}}
        return {"ok": False, "error": "action invalida"}

    def _summary(self, movements, products, parties) -> dict:
        return {
            "products": len(products),
            "customers": sum(1 for p in parties if p.get("party_type") in {"customer", "both"}),
            "suppliers": sum(1 for p in parties if p.get("party_type") in {"supplier", "both"}),
            "movements": len(movements),
            "receivables_total": sum(row["balance_amount"] for row in self._receivables(movements)),
            "top_inventory": self._stock(movements, products)[:5],
        }

    def _receivables(self, movements) -> list[dict]:
        by_customer = {}
        for movement in movements:
            if movement.get("movement_type") != "salida":
                continue
            balance = float(movement.get("balance_amount") or 0)
            if balance <= 0:
                continue
            key = movement.get("customer_id") or movement.get("customer_name_snapshot") or "sin_cliente"
            row = by_customer.setdefault(key, {"customer_id": movement.get("customer_id"), "customer_name": movement.get("customer_name_snapshot") or key, "balance_amount": 0.0, "documents": 0})
            row["balance_amount"] += balance
            row["documents"] += 1
        return sorted(by_customer.values(), key=lambda row: -row["balance_amount"])

    def _sales_by_product_month(self, movements, products, context) -> list[dict]:
        product_names = {p.get("id"): p.get("product_name") for p in products}
        month = str(context.get("month") or date.today().strftime("%Y-%m"))
        totals = {}
        for movement in movements:
            if movement.get("movement_type") != "salida":
                continue
            if not str(movement.get("movement_date") or "").startswith(month):
                continue
            product_id = movement.get("product_id")
            row = totals.setdefault(product_id, {"product_id": product_id, "product_name": product_names.get(product_id) or movement.get("product_name_snapshot") or product_id, "quantity": 0.0, "total_sale": 0.0})
            row["quantity"] += float(movement.get("quantity_out") or 0)
            row["total_sale"] += float(movement.get("total_sale") or 0)
        return sorted(totals.values(), key=lambda row: -row["total_sale"])

    def _stock(self, movements, products) -> list[dict]:
        product_names = {p.get("id"): p for p in products}
        stock = {}
        for movement in movements:
            product_id = movement.get("product_id")
            if not product_id:
                continue
            row = stock.setdefault(product_id, {"product_id": product_id, "quantity": 0.0, "total_in": 0.0, "total_out": 0.0})
            q_in = float(movement.get("quantity_in") or 0)
            q_out = float(movement.get("quantity_out") or 0)
            row["quantity"] += q_in - q_out
            row["total_in"] += q_in
            row["total_out"] += q_out
        result = []
        for product_id, row in stock.items():
            product = product_names.get(product_id, {})
            result.append({**row, "product_name": product.get("product_name") or product_id, "is_key_product": product.get("is_key_product", False)})
        return sorted(result, key=lambda row: -row["quantity"])

    def _recurrence_alerts(self, movements, products, parties, context) -> list[dict]:
        rules = context.get("recurrence_rules") or KEY_RULES
        today = self._as_date(context.get("today")) or date.today()
        key_products = {p.get("id"): p for p in products if p.get("product_key") in {r["product_key"] for r in rules}}
        customers = [p for p in parties if p.get("party_type") in {"customer", "both"}]
        last = self._last_purchase_map(movements)
        alerts = []
        for customer in customers:
            for product_id, product in key_products.items():
                rule = next((r for r in rules if r["product_key"] == product.get("product_key")), None)
                if not rule:
                    continue
                key = (customer.get("id"), product_id)
                last_movement = last.get(key)
                last_date = self._as_date(last_movement.get("movement_date")) if last_movement else None
                days = (today - last_date).days if last_date else None
                if days is None or days >= int(rule.get("threshold_days", 7)):
                    alerts.append({
                        "customer_id": customer.get("id"),
                        "customer_name": customer.get("party_name"),
                        "product_id": product_id,
                        "product_name": product.get("product_name"),
                        "product_key": product.get("product_key"),
                        "last_purchase_date": last_date.isoformat() if last_date else None,
                        "days_without_purchase": days,
                        "threshold_days": rule.get("threshold_days", 7),
                        "alert_frequency": rule.get("alert_frequency", "daily"),
                        "alert": True,
                    })
        return alerts

    def _last_purchase_by_customer(self, movements, products, parties) -> list[dict]:
        product_names = {p.get("id"): p for p in products}
        party_names = {p.get("id"): p for p in parties}
        rows = []
        for (customer_id, product_id), movement in self._last_purchase_map(movements).items():
            product = product_names.get(product_id, {})
            if product.get("product_key") not in {"varilla_3_8", "varilla_1_2", "cemento"}:
                continue
            party = party_names.get(customer_id, {})
            rows.append({
                "customer_id": customer_id,
                "customer_name": party.get("party_name") or movement.get("customer_name_snapshot"),
                "product_id": product_id,
                "product_name": product.get("product_name") or movement.get("product_name_snapshot"),
                "product_key": product.get("product_key"),
                "last_purchase_date": movement.get("movement_date"),
                "quantity": float(movement.get("quantity_out") or 0),
                "amount": float(movement.get("total_sale") or 0),
            })
        return sorted(rows, key=lambda row: (row["customer_name"] or "", row["product_name"] or ""))

    def _last_purchase_map(self, movements) -> dict:
        last = {}
        for movement in movements:
            if movement.get("movement_type") != "salida":
                continue
            customer_id = movement.get("customer_id")
            product_id = movement.get("product_id")
            if not customer_id or not product_id:
                continue
            key = (customer_id, product_id)
            previous = last.get(key)
            if previous is None or str(movement.get("movement_date") or "") >= str(previous.get("movement_date") or ""):
                last[key] = movement
        return last

    def _as_date(self, value):
        if not value:
            return None
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
