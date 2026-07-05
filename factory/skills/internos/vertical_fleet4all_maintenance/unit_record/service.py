from __future__ import annotations

from datetime import date

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


class UnitRecordService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        unit_key = str(context.get("unit_key") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not unit_key:
            return {"ok": False, "error": "missing_required_fields"}

        period = context.get("period") if isinstance(context.get("period"), dict) else {}
        period_from = period.get("from")
        period_to = period.get("to")

        db = SupabaseClient({**context, "schema": _SCHEMA})

        unit_res = db.rest_select("units", filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"}, select="*", limit=1)
        if not unit_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": unit_res.get("error")}}
        units = unit_res.get("data") or []
        if not units:
            return {"ok": False, "error": "unit_not_found"}
        unit = units[0]

        services_res = db.rest_select(
            "services", filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"},
            select="service_folio,service_date,service_type,description,cost,currency,workshop",
        )
        if not services_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": services_res.get("error")}}
        services = sorted(services_res.get("data") or [], key=lambda s: s.get("service_date") or "", reverse=True)

        plans_res = db.rest_select(
            "maintenance_plans", filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}", "status": "eq.active"},
            select="*",
        )
        if not plans_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": plans_res.get("error")}}
        plans = plans_res.get("data") or []

        today = date.today().isoformat()
        odometer = float(unit.get("odometer_km") or 0)
        upcoming = []
        for plan in plans:
            km_remaining = (plan.get("next_due_km") - odometer) if plan.get("next_due_km") is not None else None
            days_remaining = self._days_between(today, plan.get("next_due_date")) if plan.get("next_due_date") else None
            upcoming.append({**plan, "km_remaining": km_remaining, "days_remaining": days_remaining})

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

        maintenance_cost_period = sum(
            float(s.get("cost") or 0) for s in services if in_period(s.get("service_date"))
        )
        currency = services[0].get("currency") if services else "MXN"

        return {
            "ok": True,
            "data": {
                "unit": unit,
                "service_history": services,
                "active_plans": plans,
                "upcoming_due": upcoming,
                "maintenance_cost_period": {"total": round(maintenance_cost_period, 2), "currency": currency, "from": period_from, "to": period_to},
                "warnings": [],
            },
        }

    def _days_between(self, today: str, target: str) -> int | None:
        try:
            return (date.fromisoformat(target) - date.fromisoformat(today)).days
        except ValueError:
            return None
