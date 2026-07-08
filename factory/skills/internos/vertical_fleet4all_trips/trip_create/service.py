from __future__ import annotations

import re
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "T-"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


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
        warnings = []
        collection = self._setup_collection(context, created)
        if collection.get("ok"):
            if collection.get("data", {}).get("trip"):
                created = collection["data"]["trip"]
        else:
            warnings.append(f"collection_setup_failed: {collection.get('error')}")
        warnings.extend(collection.get("data", {}).get("warnings", []))
        return {"ok": True, "data": {"trip": created, "collection": collection.get("data"), "warnings": warnings}}

    def _setup_collection(self, context: dict, trip: dict) -> dict:
        empresa_id = trip.get("empresa_id")
        trip_folio = trip.get("trip_folio")
        sale_price = float(trip.get("sale_price") or 0)
        payment_mode = str(context.get("payment_mode") or context.get("forma_pago") or "").strip().lower()
        payment_status = str(context.get("payment_status") or "").strip().lower()
        payment_method = str(context.get("payment_method") or context.get("method") or "transfer").strip().lower()
        paid_amount = self._to_amount(context.get("paid_amount"))

        if payment_mode == "contado" and not payment_status:
            payment_status = "paid"
        if payment_mode in ("credito", "credit", "cob", "cobranza") and not payment_status:
            payment_status = "receivable"

        if payment_status not in ("paid", "partial", "receivable"):
            return {"ok": True, "data": {"warnings": []}}

        runner = _runner()
        warnings = []
        payment = None
        receivable = None

        if payment_status == "paid":
            amount = sale_price
        elif payment_status == "partial":
            amount = paid_amount or 0
            if amount <= 0:
                return {"ok": False, "error": "paid_amount_requerido_para_pago_parcial"}
            amount = min(amount, sale_price)
        else:
            amount = 0

        if amount > 0:
            pay_res = runner.run(
                "vertical_fleet4all_collections/payment_capture",
                {
                    **context,
                    "empresa_id": empresa_id,
                    "trip_folio": trip_folio,
                    "customer": trip.get("customer"),
                    "amount": amount,
                    "method": payment_method,
                    "payment_date": context.get("payment_date") or trip.get("departure_date"),
                    "notes": context.get("notes") or f"Pago automatico al crear viaje ({payment_mode or payment_status})",
                    "dry_run": False,
                },
            )
            if not pay_res.get("ok"):
                return pay_res
            payment = (pay_res.get("data") or {}).get("payment")
            warnings.extend((pay_res.get("data") or {}).get("warnings") or [])

        if payment_status == "receivable" or payment_status == "partial":
            sync_res = runner.run(
                "vertical_fleet4all_collections/receivables_sync",
                {
                    **context,
                    "empresa_id": empresa_id,
                    "trip_folio": trip_folio,
                    "credit_days": context.get("credit_days"),
                    "dry_run": False,
                },
            )
            if not sync_res.get("ok"):
                return sync_res
            receivable = (sync_res.get("data") or {}).get("receivable")

        if payment_status == "paid" and not receivable:
            # payment_capture already syncs and marks the trip paid.
            receivable = None

        db = SupabaseClient({**context, "schema": _SCHEMA})
        refreshed = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="*",
            limit=1,
        )
        trip_data = (refreshed.get("data") or [trip])[0] if refreshed.get("ok") else trip
        return {"ok": True, "data": {"trip": trip_data, "payment": payment, "receivable": receivable, "warnings": warnings}}

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
