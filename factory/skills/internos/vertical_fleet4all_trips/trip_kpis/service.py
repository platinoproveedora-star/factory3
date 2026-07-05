from __future__ import annotations

from datetime import date, timedelta

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


class TripKpisService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        period = context.get("period") if isinstance(context.get("period"), dict) else {}
        period_from = period.get("from")
        period_to = period.get("to")

        db = SupabaseClient({**context, "schema": _SCHEMA})

        trips_res = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="trip_folio,departure_date,trip_profit,trip_status,unit_key,driver_key",
        )
        if not trips_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": trips_res.get("error")}}
        trips = trips_res.get("data") or []

        expenses_res = db.rest_select(
            "expenses",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="expense_type,amount,expense_date",
        )
        if not expenses_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": expenses_res.get("error")}}
        expenses = expenses_res.get("data") or []

        today = date.today()
        week_ago = (today - timedelta(days=7)).isoformat()
        month_ago = (today - timedelta(days=30)).isoformat()

        def in_period(value: str | None) -> bool:
            if not (period_from or period_to):
                return True
            if not value:
                return False
            if period_from and value < period_from:
                return False
            if period_to and value > period_to:
                return False
            return True

        scoped_trips = [t for t in trips if in_period(t.get("departure_date"))]
        scoped_expenses = [e for e in expenses if in_period(e.get("expense_date"))]

        active_trips = sum(1 for t in trips if t.get("trip_status") == "active")
        utilidad_semana = sum(
            float(t.get("trip_profit") or 0) for t in trips if (t.get("departure_date") or "") >= week_ago
        )
        utilidad_mes = sum(
            float(t.get("trip_profit") or 0) for t in trips if (t.get("departure_date") or "") >= month_ago
        )

        profit_by_unit: dict[str, float] = {}
        for t in scoped_trips:
            key = t.get("unit_key") or "sin_unidad"
            profit_by_unit[key] = profit_by_unit.get(key, 0.0) + float(t.get("trip_profit") or 0)

        profit_by_driver: dict[str, float] = {}
        for t in scoped_trips:
            key = t.get("driver_key") or "sin_operador"
            profit_by_driver[key] = profit_by_driver.get(key, 0.0) + float(t.get("trip_profit") or 0)

        expenses_by_type: dict[str, float] = {}
        for e in scoped_expenses:
            key = e.get("expense_type") or "other"
            expenses_by_type[key] = expenses_by_type.get(key, 0.0) + float(e.get("amount") or 0)
        top_expenses = sorted(expenses_by_type.items(), key=lambda kv: kv[1], reverse=True)

        return {
            "ok": True,
            "data": {
                "trip_kpis": {
                    "empresa_id": empresa_id,
                    "period": {"from": period_from, "to": period_to},
                    "active_trips": active_trips,
                    "utilidad_semana": round(utilidad_semana, 2),
                    "utilidad_mes": round(utilidad_mes, 2),
                    "profit_by_unit": {k: round(v, 2) for k, v in profit_by_unit.items()},
                    "profit_by_driver": {k: round(v, 2) for k, v in profit_by_driver.items()},
                    "top_expenses_by_type": [
                        {"expense_type": k, "amount": round(v, 2)} for k, v in top_expenses
                    ],
                },
                "warnings": [],
            },
        }
