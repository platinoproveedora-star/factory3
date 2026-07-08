from __future__ import annotations

from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class TripManageService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        action = str(context.get("action") or "update").strip().lower()
        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})
        if action == "update":
            return self._update(db, context, empresa_id)
        if action == "delete":
            return self._delete(db, context, empresa_id)
        return {"ok": False, "error": "action_invalida"}

    def _update(self, db: SupabaseClient, context: dict, empresa_id: str) -> dict:
        trip_folio = self._trip_folio(context)
        if not trip_folio:
            return {"ok": False, "error": "trip_folio_requerido"}

        values = {}
        for field in (
            "customer",
            "origin",
            "destination",
            "departure_date",
            "arrival_date",
            "currency",
            "driver_key",
            "unit_key",
            "trip_status",
            "payment_status",
        ):
            if field in context:
                raw = context.get(field)
                values[field] = str(raw).strip() or None if raw is not None else None

        for field in ("sale_price", "distance_km"):
            if field in context:
                amount = self._to_amount(context.get(field))
                if amount is None or amount < 0:
                    return {"ok": False, "error": f"{field}_invalido"}
                values[field] = amount

        sync_fields = {"sale_price", "customer", "departure_date", "currency"}
        sync_receivable = bool(sync_fields.intersection(values)) and self._has_receivable(db, empresa_id, trip_folio)

        if "sale_price" in values:
            current = self._get_trip(db, empresa_id, trip_folio)
            if not current.get("ok"):
                return current
            expenses_total = self._expenses_total(db, empresa_id, trip_folio)
            if not expenses_total.get("ok"):
                return expenses_total
            values["trip_cost"] = expenses_total["data"]["total"]
            values["trip_profit"] = round(float(values["sale_price"] or 0) - values["trip_cost"], 2)

        if not values:
            return {"ok": False, "error": "sin_campos_para_actualizar"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo fleet4all.trips", "data": {"trip": {"trip_folio": trip_folio, **values}}}

        res = db.rest_update(
            "trips",
            values=values,
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
        )
        if not res.get("ok"):
            return {"ok": False, "error": "db_update_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "trip_not_found"}

        trip = rows[0]
        warnings = []
        if sync_receivable:
            sync_res = _runner().run(
                "vertical_fleet4all_collections/receivables_sync",
                {**context, "empresa_id": empresa_id, "trip_folio": trip_folio, "dry_run": False},
            )
            if not sync_res.get("ok"):
                warnings.append(f"receivables_sync_failed: {sync_res.get('error')}")
            else:
                refreshed = self._get_trip(db, empresa_id, trip_folio)
                if refreshed.get("ok"):
                    trip = refreshed["data"]["trip"]
        return {"ok": True, "data": {"trip": trip, "warnings": warnings}}

    def _delete(self, db: SupabaseClient, context: dict, empresa_id: str) -> dict:
        trip_folio = self._trip_folio(context)
        if not trip_folio:
            return {"ok": False, "error": "trip_folio_requerido"}

        trip = self._get_trip(db, empresa_id, trip_folio)
        if not trip.get("ok"):
            return trip

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se borro fleet4all.trips",
                "data": {
                    "trip": trip["data"]["trip"],
                    "freed": {"expenses": "pending", "payments": "pending"},
                    "deleted": {"receivables": "pending", "trips": "pending"},
                },
            }

        filters = {"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"}
        freed_expenses = db.rest_update("expenses", values={"trip_folio": None}, filters=filters)
        if not freed_expenses.get("ok"):
            return {"ok": False, "error": "expenses_unlink_failed", "data": {"detail": freed_expenses.get("error")}}

        freed_payments = db.rest_update("payments", values={"trip_folio": None}, filters=filters)
        if not freed_payments.get("ok"):
            return {"ok": False, "error": "payments_unlink_failed", "data": {"detail": freed_payments.get("error")}}

        deleted_receivables = db.rest_delete("receivables", filters=filters)
        if not deleted_receivables.get("ok"):
            return {"ok": False, "error": "receivables_delete_failed", "data": {"detail": deleted_receivables.get("error")}}

        deleted_trip = db.rest_delete("trips", filters=filters)
        if not deleted_trip.get("ok"):
            return {"ok": False, "error": "trip_delete_failed", "data": {"detail": deleted_trip.get("error")}}
        trip_rows = deleted_trip.get("data") or []
        if not trip_rows:
            return {"ok": False, "error": "trip_not_found"}

        return {
            "ok": True,
            "data": {
                "trip": trip_rows[0],
                "freed": {
                    "expenses": len(freed_expenses.get("data") or []),
                    "payments": len(freed_payments.get("data") or []),
                },
                "deleted": {
                    "receivables": len(deleted_receivables.get("data") or []),
                    "trips": len(trip_rows),
                },
                "warnings": [],
            },
        }

    def _get_trip(self, db: SupabaseClient, empresa_id: str, trip_folio: str) -> dict:
        res = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="*",
            limit=1,
        )
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "trip_not_found"}
        return {"ok": True, "data": {"trip": rows[0]}}

    def _expenses_total(self, db: SupabaseClient, empresa_id: str, trip_folio: str) -> dict:
        res = db.rest_select(
            "expenses",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="amount",
        )
        if not res.get("ok"):
            return {"ok": False, "error": "expenses_query_failed", "data": {"detail": res.get("error")}}
        total = round(sum(float(row.get("amount") or 0) for row in (res.get("data") or [])), 2)
        return {"ok": True, "data": {"total": total}}

    def _has_receivable(self, db: SupabaseClient, empresa_id: str, trip_folio: str) -> bool:
        res = db.rest_select(
            "receivables",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="receivable_folio",
            limit=1,
        )
        return bool(res.get("ok") and (res.get("data") or []))

    def _trip_folio(self, context: dict) -> str:
        return str(context.get("trip_folio") or context.get("folio") or "").strip().upper()

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
