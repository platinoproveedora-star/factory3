"""Motor de recalculo de inventario. Filosofia: el saldo de un producto NO es
un contador que se incrementa/decrementa en tiempo real — es una vista
derivada, recalculable, de los movimientos fiscales reales (cfdi_item_movements)
agrupados por mes. Esto es necesario porque un XML de compra o venta puede
llegar semanas o meses despues de su fecha real (descarga masiva del SAT,
factura de proveedor tardia), y cuando eso pasa hay que recalcular ese mes y
repropagar el saldo hacia todos los meses siguientes hasta hoy — el saldo
inicial de cada mes siempre es el saldo final del anterior.

Como el calculo es una suma completa de movimientos (no un delta sobre un
valor previo), es naturalmente idempotente ante corridas concurrentes: dos
recalculos del mismo producto en paralelo convergen al mismo resultado sin
necesitar locks."""
from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_MAX_PERIODS = 240  # 20 anios de proteccion contra loops


class InventoryRecalculateService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        product_id = str(context.get("product_id") or "").strip()
        warehouse_id = str(context.get("warehouse_id") or "").strip()
        environment = str(context.get("environment") or "sandbox").strip().lower()
        if not company_id or not product_id or not warehouse_id:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["company_id", "product_id", "warehouse_id"]}}

        today = datetime.now(timezone.utc)
        from_year = int(context.get("from_year") or today.year)
        from_month = int(context.get("from_month") or today.month)
        if not (1 <= from_month <= 12):
            return {"ok": False, "error": "from_month_invalido"}

        dry_run = context.get("dry_run", True)
        db = SupabaseClient({**context, "schema": _SCHEMA})

        year, month = from_year, from_month
        target = (today.year, today.month)
        periods: list[dict] = []
        iterations = 0

        while (year, month) <= target and iterations < _MAX_PERIODS:
            iterations += 1
            opening = self._opening_balance(db, company_id, product_id, warehouse_id, environment, year, month)
            in_qty, out_qty = self._sum_period(db, company_id, product_id, warehouse_id, environment, year, month)
            closing = round(opening + in_qty - out_qty, 4)

            period_row = {
                "company_id": company_id,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "environment": environment,
                "year": year,
                "month": month,
                "opening_qty": opening,
                "in_qty": in_qty,
                "out_qty": out_qty,
                "closing_qty": closing,
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }
            if not dry_run:
                db.rest_upsert("inventory_period_balance", period_row, "company_id,product_id,warehouse_id,environment,year,month")
            periods.append({"year": year, "month": month, "opening_qty": opening, "in_qty": in_qty, "out_qty": out_qty, "closing_qty": closing})

            month += 1
            if month > 12:
                month = 1
                year += 1

        current_stock = periods[-1]["closing_qty"] if periods else 0.0
        if not dry_run:
            db.rest_upsert(
                "product_stock",
                {"company_id": company_id, "product_id": product_id, "warehouse_id": warehouse_id, "environment": environment, "current_stock": current_stock, "updated_at": datetime.now(timezone.utc).isoformat()},
                "company_id,product_id,warehouse_id,environment",
            )

        return {"ok": True, "data": {"periods_recalculated": len(periods), "periods": periods, "current_stock": current_stock}}

    def _opening_balance(self, db: SupabaseClient, company_id: str, product_id: str, warehouse_id: str, environment: str, year: int, month: int) -> float:
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        res = db.rest_select(
            "inventory_period_balance",
            filters={
                "company_id": f"eq.{company_id}", "product_id": f"eq.{product_id}", "warehouse_id": f"eq.{warehouse_id}",
                "environment": f"eq.{environment}", "year": f"eq.{prev_year}", "month": f"eq.{prev_month}",
            },
            select="closing_qty", limit=1,
        )
        rows = res.get("data") or [] if res.get("ok") else []
        return float(rows[0]["closing_qty"]) if rows else 0.0

    def _sum_period(self, db: SupabaseClient, company_id: str, product_id: str, warehouse_id: str, environment: str, year: int, month: int) -> tuple[float, float]:
        # rest_select solo soporta una condicion por columna (dict), y un rango
        # de fecha necesita gte+lt sobre la misma columna — se filtra en Python.
        period_start = f"{year:04d}-{month:02d}-01T00:00:00"
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        period_end = f"{next_year:04d}-{next_month:02d}-01T00:00:00"

        res = db.rest_select(
            "cfdi_item_movements",
            filters={
                "company_id": f"eq.{company_id}", "product_id": f"eq.{product_id}", "warehouse_id": f"eq.{warehouse_id}",
                "environment": f"eq.{environment}",
            },
            select="movement_direction,quantity,issued_at", limit=5000,
        )
        rows = res.get("data") or [] if res.get("ok") else []
        rows = [r for r in rows if r.get("issued_at") and period_start <= r["issued_at"] < period_end]
        in_qty = sum(float(r["quantity"] or 0) for r in rows if r["movement_direction"] == "in")
        out_qty = sum(float(r["quantity"] or 0) for r in rows if r["movement_direction"] == "out")
        out_cancelled = sum(float(r["quantity"] or 0) for r in rows if r["movement_direction"] == "out_cancelled")
        return round(in_qty, 4), round(out_qty - out_cancelled, 4)
