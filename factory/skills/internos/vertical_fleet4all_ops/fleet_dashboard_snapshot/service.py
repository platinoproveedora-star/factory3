from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from factory.engine import SupabaseClient

_DEFAULT_SCHEMA = "fleet4all"
_KM_DUE_THRESHOLD = 1000
_DAYS_DUE_THRESHOLD = 15


class FleetDashboardSnapshotService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        period = self._period(context)
        db = SupabaseClient({**context, "schema": context.get("schema") or _DEFAULT_SCHEMA})

        trips_res = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="trip_folio,customer,origin,destination,departure_date,trip_profit,trip_status,payment_status,driver_key,unit_key",
            order="departure_date.desc",
        )
        if not trips_res.get("ok"):
            return self._db_error(trips_res)
        trips = trips_res.get("data") or []

        receivables_res = db.rest_select(
            "receivables",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="receivable_folio,trip_folio,customer,balance,currency,due_date,collection_status",
            order="due_date.asc",
        )
        if not receivables_res.get("ok"):
            return self._db_error(receivables_res)
        receivables = receivables_res.get("data") or []

        maintenance_res = db.rest_select(
            "maintenance_plans",
            filters={"empresa_id": f"eq.{empresa_id}", "status": "eq.active"},
            select="plan_folio,unit_key,service_type,next_due_km,next_due_date",
            order="next_due_date.asc",
        )
        if not maintenance_res.get("ok"):
            return self._db_error(maintenance_res)
        maintenance_plans = maintenance_res.get("data") or []

        units_res = db.rest_select(
            "units",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="unit_key,plate,odometer_km,status",
        )
        if not units_res.get("ok"):
            return self._db_error(units_res)
        units = units_res.get("data") or []

        fuel_res = db.rest_select(
            "fuel_efficiency",
            filters={"empresa_id": f"eq.{empresa_id}"},
            select="unit_key,period_from,period_to,km_per_liter,deviation_pct,flag",
            order="period_to.desc",
        )
        if not fuel_res.get("ok"):
            return self._db_error(fuel_res)
        fuel_efficiency = fuel_res.get("data") or []

        today = date.today().isoformat()
        scoped_trips = [trip for trip in trips if self._in_period(trip.get("departure_date"), period)]
        active_trips = [trip for trip in trips if trip.get("trip_status") == "active"]
        missing_resources = [
            trip for trip in active_trips if not trip.get("driver_key") or not trip.get("unit_key")
        ]
        overdue_receivables = [
            row for row in receivables
            if float(row.get("balance") or 0) > 0
            and (row.get("collection_status") == "overdue" or str(row.get("due_date") or "9999-12-31") < today)
        ]
        due_soon = self._maintenance_due_soon(maintenance_plans, units, today)
        fuel_alerts = [
            row for row in fuel_efficiency
            if row.get("flag") in ("warning", "alert") and self._fuel_in_period(row, period)
        ]

        period_profit = round(sum(float(trip.get("trip_profit") or 0) for trip in scoped_trips), 2)
        overdue_amount = round(sum(float(row.get("balance") or 0) for row in overdue_receivables), 2)

        critical_items = []
        critical_items.extend(self._trip_items(missing_resources))
        critical_items.extend(self._receivable_items(overdue_receivables))
        critical_items.extend(self._maintenance_items(due_soon))
        critical_items.extend(self._fuel_items(fuel_alerts))
        critical_items = sorted(critical_items, key=lambda item: self._severity_rank(item["severity"]))[:12]

        summary = {
            "empresa_id": empresa_id,
            "period": period,
            "active_trips": len(active_trips),
            "trips_missing_resources": len(missing_resources),
            "period_profit": period_profit,
            "overdue_receivables": overdue_amount,
            "overdue_receivables_count": len(overdue_receivables),
            "maintenance_due_soon": len(due_soon),
            "fuel_alerts": len(fuel_alerts),
            "currency": "MXN",
        }
        health = [
            {"module": "Viajes", "status": "warning" if missing_resources else "ok", "count": len(missing_resources), "href": "/dashboard/viajes"},
            {"module": "Cobranza", "status": "alert" if overdue_receivables else "ok", "count": len(overdue_receivables), "href": "/dashboard/cobranza"},
            {"module": "Mantenimiento", "status": "warning" if due_soon else "ok", "count": len(due_soon), "href": "/dashboard/mantenimiento"},
            {"module": "Combustible", "status": "alert" if any(row.get("flag") == "alert" for row in fuel_alerts) else ("warning" if fuel_alerts else "ok"), "count": len(fuel_alerts), "href": "/dashboard/combustible"},
        ]
        return {"ok": True, "data": {"summary": summary, "health": health, "critical_items": critical_items, "warnings": []}}

    def _period(self, context: dict) -> dict:
        raw = context.get("period") if isinstance(context.get("period"), dict) else {}
        if raw.get("from") or raw.get("to"):
            return {"from": raw.get("from"), "to": raw.get("to")}
        today = date.today()
        return {"from": today.replace(day=1).isoformat(), "to": today.isoformat()}

    def _in_period(self, value: str | None, period: dict) -> bool:
        if not value:
            return False
        if period.get("from") and value < period["from"]:
            return False
        if period.get("to") and value > period["to"]:
            return False
        return True

    def _fuel_in_period(self, row: dict, period: dict) -> bool:
        return self._in_period(row.get("period_to") or row.get("period_from"), period)

    def _maintenance_due_soon(self, plans: list[dict], units: list[dict], today: str) -> list[dict]:
        odometer_by_unit = {unit.get("unit_key"): float(unit.get("odometer_km") or 0) for unit in units}
        due_soon = []
        for plan in plans:
            odometer = odometer_by_unit.get(plan.get("unit_key"))
            km_remaining = (
                float(plan.get("next_due_km")) - odometer
                if plan.get("next_due_km") is not None and odometer is not None
                else None
            )
            days_remaining = self._days_between(today, plan.get("next_due_date")) if plan.get("next_due_date") else None
            if (
                km_remaining is not None and km_remaining <= _KM_DUE_THRESHOLD
            ) or (
                days_remaining is not None and days_remaining <= _DAYS_DUE_THRESHOLD
            ):
                due_soon.append({**plan, "km_remaining": km_remaining, "days_remaining": days_remaining})
        return due_soon

    def _days_between(self, today: str, target: str | None) -> int | None:
        if not target:
            return None
        try:
            return (date.fromisoformat(target) - date.fromisoformat(today)).days
        except ValueError:
            return None

    def _trip_items(self, trips: list[dict]) -> list[dict]:
        items = []
        for trip in trips[:4]:
            missing = []
            if not trip.get("unit_key"):
                missing.append("unidad")
            if not trip.get("driver_key"):
                missing.append("operador")
            items.append({
                "type": "trip_missing_resources",
                "severity": "warning",
                "title": f"Viaje {trip.get('trip_folio')} sin {'/'.join(missing)}",
                "description": f"{trip.get('origin') or '-'} -> {trip.get('destination') or '-'}",
                "href": "/dashboard/viajes",
                "ref": trip.get("trip_folio"),
            })
        return items

    def _receivable_items(self, receivables: list[dict]) -> list[dict]:
        items = []
        for row in receivables[:4]:
            items.append({
                "type": "overdue_receivable",
                "severity": "alert",
                "title": f"Cobranza vencida {row.get('trip_folio') or row.get('receivable_folio')}",
                "description": f"{row.get('customer') or '-'} · {self._money(row.get('balance'), row.get('currency'))}",
                "href": "/dashboard/cobranza",
                "ref": row.get("receivable_folio"),
            })
        return items

    def _maintenance_items(self, plans: list[dict]) -> list[dict]:
        items = []
        for plan in plans[:3]:
            pieces = []
            if plan.get("km_remaining") is not None:
                pieces.append(f"{round(float(plan['km_remaining']), 1)} km")
            if plan.get("days_remaining") is not None:
                pieces.append(f"{plan['days_remaining']} dias")
            items.append({
                "type": "maintenance_due_soon",
                "severity": "warning",
                "title": f"Mantenimiento proximo {plan.get('unit_key')}",
                "description": f"{plan.get('service_type') or '-'} · {' / '.join(pieces) or 'por revisar'}",
                "href": "/dashboard/mantenimiento",
                "ref": plan.get("plan_folio"),
            })
        return items

    def _fuel_items(self, alerts: list[dict]) -> list[dict]:
        items = []
        for row in alerts[:3]:
            items.append({
                "type": "fuel_efficiency_alert",
                "severity": "alert" if row.get("flag") == "alert" else "warning",
                "title": f"Rendimiento {row.get('flag')} en {row.get('unit_key')}",
                "description": f"{row.get('km_per_liter') or '-'} km/l · desviacion {row.get('deviation_pct') or '-'}%",
                "href": "/dashboard/combustible",
                "ref": row.get("unit_key"),
            })
        return items

    def _money(self, value: Any, currency: str | None) -> str:
        return f"{round(float(value or 0), 2)} {currency or 'MXN'}"

    def _severity_rank(self, severity: str) -> int:
        return {"alert": 0, "warning": 1, "ok": 2}.get(severity, 9)

    def _db_error(self, result: dict) -> dict:
        return {"ok": False, "error": "db_read_failed", "data": {"detail": result.get("error")}}
