from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


class TripCloseService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        trip_folio = str(context.get("trip_folio") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not trip_folio:
            return {"ok": False, "error": "missing_required_fields"}

        db = SupabaseClient({**context, "schema": _SCHEMA})

        trip_res = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="*",
            limit=1,
        )
        if not trip_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": trip_res.get("error")}}
        trips = trip_res.get("data") or []
        if not trips:
            return {"ok": False, "error": "trip_not_found"}
        trip = trips[0]

        expenses_res = db.rest_select(
            "expenses",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="amount",
        )
        if not expenses_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": expenses_res.get("error")}}
        trip_cost = sum(float(e.get("amount") or 0) for e in (expenses_res.get("data") or []))
        sale_price = float(trip.get("sale_price") or 0)
        trip_profit = sale_price - trip_cost

        was_closed = trip.get("trip_status") == "closed"
        warnings = ["recalculated"] if was_closed else []

        updated = {**trip, "trip_cost": trip_cost, "trip_profit": trip_profit, "trip_status": "closed"}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se persistio el cierre",
                "data": {"trip": updated, "warnings": warnings + ["dry_run: no se persistio"]},
            }

        patch_res = db.rest_update(
            "trips",
            values={"trip_cost": trip_cost, "trip_profit": trip_profit, "trip_status": "closed"},
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
        )
        if not patch_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": patch_res.get("error")}}

        persisted = (patch_res.get("data") or [updated])[0]
        return {"ok": True, "data": {"trip": persisted, "warnings": warnings}}
