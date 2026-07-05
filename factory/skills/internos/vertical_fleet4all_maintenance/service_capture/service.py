from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "SV-"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class ServiceCaptureService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        unit_key = str(context.get("unit_key") or "").strip()
        service_type = str(context.get("service_type") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not unit_key or not service_type:
            return {"ok": False, "error": "missing_required_fields"}

        cost = self._to_amount(context.get("cost")) or 0.0
        if cost < 0:
            return {"ok": False, "error": "invalid_amount"}

        odometer_km = self._to_amount(context.get("odometer_km"))
        base = {
            "empresa_id": empresa_id,
            "unit_key": unit_key,
            "plan_folio": context.get("plan_folio"),
            "service_date": context.get("service_date"),
            "odometer_km": odometer_km,
            "service_type": service_type,
            "description": context.get("description"),
            "cost": cost,
            "currency": str(context.get("currency") or "MXN").strip().upper(),
            "workshop": context.get("workshop"),
            "doc_id": context.get("doc_id"),
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.services",
                "data": {"service": {**base, "service_folio": None}, "warnings": ["dry_run: folio no asignado, plan no verificado"]},
            }

        db = SupabaseClient({**context, "schema": _SCHEMA})
        warnings: list[str] = []

        if base["plan_folio"]:
            plan_res = db.rest_select(
                "maintenance_plans",
                filters={"empresa_id": f"eq.{empresa_id}", "plan_folio": f"eq.{base['plan_folio']}"},
                select="*", limit=1,
            )
            if not plan_res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": plan_res.get("error")}}
            plans = plan_res.get("data") or []
            if not plans:
                return {"ok": False, "error": "plan_not_found"}
            plan = plans[0]

            new_last_km = odometer_km if odometer_km is not None else plan.get("last_service_km")
            next_due_km = (
                new_last_km + float(plan["every_km"])
                if plan.get("every_km") is not None and new_last_km is not None
                else None
            )
            next_due_date = (
                self._add_days(base["service_date"], int(plan["every_days"]))
                if plan.get("every_days") and base["service_date"]
                else None
            )
            plan_upd = db.rest_update(
                "maintenance_plans",
                values={
                    "last_service_km": new_last_km,
                    "last_service_date": base["service_date"],
                    "next_due_km": next_due_km,
                    "next_due_date": next_due_date,
                },
                filters={"empresa_id": f"eq.{empresa_id}", "plan_folio": f"eq.{base['plan_folio']}"},
            )
            if not plan_upd.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": plan_upd.get("error")}}

        if odometer_km is not None:
            unit_res = db.rest_select(
                "units", filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"}, select="odometer_km", limit=1
            )
            if not unit_res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": unit_res.get("error")}}
            units = unit_res.get("data") or []
            if not units:
                return {"ok": False, "error": "unit_not_found"}
            current_odometer = float(units[0].get("odometer_km") or 0)
            if odometer_km > current_odometer:
                db.rest_update("units", values={"odometer_km": odometer_km}, filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"})
            else:
                warnings.append("odometer_lower")

        folio = self._next_folio(db, empresa_id)
        row = {**base, "service_folio": folio}
        res = db.rest_insert("services", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        created = (res.get("data") or [row])[0]

        if context.get("as_expense"):
            expense_res = _runner().run(
                "vertical_fleet4all_trips/expense_capture",
                {
                    "empresa_id": empresa_id,
                    "amount": cost,
                    "concept": f"service {unit_key}: {service_type}",
                    "expense_type": "repair",
                    "expense_date": base["service_date"],
                    "dry_run": False,
                },
            )
            if not expense_res.get("ok"):
                warnings.append(f"as_expense_failed: {expense_res.get('error')}")

        return {"ok": True, "data": {"service": created, "warnings": warnings}}

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
            "services",
            filters={"empresa_id": f"eq.{empresa_id}", "service_folio": f"like.{_FOLIO_PREFIX}*"},
            select="service_folio",
            order="service_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("service_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
