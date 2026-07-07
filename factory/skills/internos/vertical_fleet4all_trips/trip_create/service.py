from __future__ import annotations

import re

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "T-"


class TripCreateService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        customer = str(context.get("customer") or "").strip() or None
        origin = str(context.get("origin") or "").strip() or None
        destination = str(context.get("destination") or "").strip() or None
        if not customer and not (origin and destination):
            return {"ok": False, "error": "missing_required_fields"}

        sale_price = self._to_amount(context.get("sale_price"))
        if sale_price is None or sale_price < 0:
            return {"ok": False, "error": "invalid_amount"}

        base = {
            "empresa_id": empresa_id,
            "customer": customer,
            "origin": origin,
            "destination": destination,
            "sale_price": sale_price,
            "currency": str(context.get("currency") or "MXN").strip().upper(),
            "driver_key": context.get("driver_key"),
            "unit_key": context.get("unit_key"),
            "distance_km": self._to_amount(context.get("distance_km")),
            "departure_date": context.get("departure_date"),
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.trips",
                "data": {
                    "trip": {
                        **base,
                        "trip_folio": None,
                        "trip_cost": 0,
                        "trip_profit": 0,
                        "trip_status": "active",
                        "payment_status": "receivable",
                    },
                    "warnings": ["dry_run: folio no asignado"],
                },
            }

        db = SupabaseClient({**context, "schema": _SCHEMA})
        folio = self._next_folio(db, empresa_id)
        row = {
            **base,
            "trip_folio": folio,
            "trip_cost": 0,
            "trip_profit": 0,
            "trip_status": "active",
            "payment_status": "receivable",
        }
        res = db.rest_insert("trips", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}

        created = (res.get("data") or [row])[0]
        return {"ok": True, "data": {"trip": created, "warnings": []}}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"like.{_FOLIO_PREFIX}*"},
            select="trip_folio",
            order="trip_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("trip_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
