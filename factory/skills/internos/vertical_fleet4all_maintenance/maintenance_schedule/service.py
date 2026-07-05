from __future__ import annotations

import re
from datetime import date, timedelta

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "M-"
_DEFAULT_KM_THRESHOLD = 1000
_DEFAULT_DAYS_THRESHOLD = 15


class MaintenanceScheduleService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        if context.get("due_soon"):
            return self._due_soon(context, empresa_id)
        return self._create(context, empresa_id)

    def _create(self, context: dict, empresa_id: str) -> dict:
        unit_key = str(context.get("unit_key") or "").strip()
        service_type = str(context.get("service_type") or "").strip()
        every_km = self._to_amount(context.get("every_km"))
        every_days = context.get("every_days")
        if not unit_key or not service_type or (every_km is None and not every_days):
            return {"ok": False, "error": "missing_required_fields"}

        last_service_km = self._to_amount(context.get("last_service_km")) or 0.0
        last_service_date = context.get("last_service_date")

        next_due_km = last_service_km + every_km if every_km is not None else None
        next_due_date = self._add_days(last_service_date, int(every_days)) if last_service_date and every_days else None

        base = {
            "empresa_id": empresa_id,
            "unit_key": unit_key,
            "service_type": service_type,
            "every_km": every_km,
            "every_days": int(every_days) if every_days else None,
            "last_service_km": last_service_km,
            "last_service_date": last_service_date,
            "next_due_km": next_due_km,
            "next_due_date": next_due_date,
            "status": "active",
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.maintenance_plans",
                "data": {"maintenance_plan": {**base, "plan_folio": None}, "warnings": ["dry_run: folio no asignado"]},
            }

        db = SupabaseClient({**context, "schema": _SCHEMA})
        folio = self._next_folio(db, empresa_id)
        row = {**base, "plan_folio": folio}
        res = db.rest_insert("maintenance_plans", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        created = (res.get("data") or [row])[0]
        return {"ok": True, "data": {"maintenance_plan": created, "warnings": []}}

    def _due_soon(self, context: dict, empresa_id: str) -> dict:
        km_threshold = self._to_amount(context.get("km_threshold")) or _DEFAULT_KM_THRESHOLD
        days_threshold = int(context.get("days_threshold") or _DEFAULT_DAYS_THRESHOLD)

        db = SupabaseClient({**context, "schema": _SCHEMA})
        filters = {"empresa_id": f"eq.{empresa_id}", "status": "eq.active"}
        if context.get("unit_key"):
            filters["unit_key"] = f"eq.{context['unit_key']}"
        plans_res = db.rest_select("maintenance_plans", filters=filters, select="*")
        if not plans_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": plans_res.get("error")}}
        plans = plans_res.get("data") or []

        units_res = db.rest_select("units", filters={"empresa_id": f"eq.{empresa_id}"}, select="unit_key,odometer_km")
        if not units_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": units_res.get("error")}}
        odometer_by_unit = {u.get("unit_key"): float(u.get("odometer_km") or 0) for u in (units_res.get("data") or [])}

        today = date.today().isoformat()
        due_soon = []
        for plan in plans:
            odometer = odometer_by_unit.get(plan.get("unit_key"))
            km_remaining = (plan.get("next_due_km") - odometer) if plan.get("next_due_km") is not None and odometer is not None else None
            days_remaining = self._days_between(today, plan.get("next_due_date")) if plan.get("next_due_date") else None
            is_due = (km_remaining is not None and km_remaining <= km_threshold) or (days_remaining is not None and days_remaining <= days_threshold)
            if is_due:
                due_soon.append({**plan, "km_remaining": km_remaining, "days_remaining": days_remaining})

        return {"ok": True, "data": {"plans_due_soon": due_soon, "warnings": []}}

    def _days_between(self, today: str, target: str) -> int | None:
        try:
            return (date.fromisoformat(target) - date.fromisoformat(today)).days
        except ValueError:
            return None

    def _add_days(self, date_str: str | None, days: int) -> str | None:
        if not date_str:
            return None
        try:
            return (date.fromisoformat(date_str) + timedelta(days=days)).isoformat()
        except ValueError:
            return None

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "maintenance_plans",
            filters={"empresa_id": f"eq.{empresa_id}", "plan_folio": f"like.{_FOLIO_PREFIX}*"},
            select="plan_folio",
            order="plan_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("plan_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
