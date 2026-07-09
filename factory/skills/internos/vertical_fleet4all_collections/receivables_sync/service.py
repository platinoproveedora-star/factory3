from __future__ import annotations

import re
from datetime import date, timedelta

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_DEFAULT_CREDIT_DAYS = 30


class ReceivablesSyncService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        all_mode = bool(context.get("all"))
        trip_folio = str(context.get("trip_folio") or "").strip()
        if not all_mode and not trip_folio:
            return {"ok": False, "error": "missing_required_fields"}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        dry_run = context.get("dry_run", True)
        credit_days = self._to_credit_days(context.get("credit_days"))

        if all_mode:
            trips_res = db.rest_select("trips", filters={"empresa_id": f"eq.{empresa_id}"}, select="*")
        else:
            trips_res = db.rest_select(
                "trips",
                filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
                select="*",
                limit=1,
            )
        if not trips_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": trips_res.get("error")}}
        trips = trips_res.get("data") or []
        if not all_mode and not trips:
            return {"ok": False, "error": "trip_not_found"}

        synced = []
        errors = []
        for trip in trips:
            result = self._sync_one(db, trip, dry_run, credit_days)
            if result.get("ok"):
                synced.append(result["data"])
            else:
                errors.append({"trip_folio": trip.get("trip_folio"), "error": result.get("error")})

        if not all_mode:
            if errors:
                return {"ok": False, "error": errors[0]["error"]}
            return {"ok": True, "data": {"receivable": synced[0], "warnings": []}}

        return {
            "ok": True,
            "data": {"synced": len(synced), "errors": errors, "receivables": synced, "warnings": []},
        }

    def _sync_one(self, db: SupabaseClient, trip: dict, dry_run: bool, credit_days: int) -> dict:
        empresa_id = trip.get("empresa_id")
        trip_folio = trip.get("trip_folio")
        total_amount = float(trip.get("sale_price") or 0)

        payments_res = db.rest_select(
            "payments",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}", "status": "eq.active"},
            select="amount",
        )
        if not payments_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed"}
        paid_amount = sum(float(p.get("amount") or 0) for p in (payments_res.get("data") or []))
        balance = max(0.0, total_amount - paid_amount)

        existing_res = db.rest_select(
            "receivables",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="*",
            limit=1,
        )
        if not existing_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed"}
        existing_rows = existing_res.get("data") or []
        existing = existing_rows[0] if existing_rows else None

        due_date = (existing.get("due_date") if existing else None) or self._add_days(
            trip.get("departure_date"), credit_days
        )
        today = date.today().isoformat()
        collection_status = self._collection_status(total_amount, paid_amount, due_date, today)
        payment_status = self._payment_status(total_amount, paid_amount)
        receivable_folio = existing.get("receivable_folio") if existing else self._folio_from_trip(trip_folio)

        row = {
            "empresa_id": empresa_id,
            "receivable_folio": receivable_folio,
            "trip_folio": trip_folio,
            "customer": trip.get("customer"),
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "balance": balance,
            "currency": trip.get("currency") or "MXN",
            "trip_date": trip.get("departure_date"),
            "due_date": due_date,
            "collection_status": collection_status,
        }

        if dry_run:
            return {"ok": True, "data": row}

        if existing:
            upd = db.rest_update(
                "receivables", values=row,
                filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            )
            if not upd.get("ok"):
                return {"ok": False, "error": "db_persistence_failed"}
            persisted = (upd.get("data") or [row])[0]
        else:
            ins = db.rest_insert("receivables", row)
            if not ins.get("ok"):
                return {"ok": False, "error": "db_persistence_failed"}
            persisted = (ins.get("data") or [row])[0]

        trip_upd = db.rest_update(
            "trips", values={"payment_status": payment_status},
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
        )
        if not trip_upd.get("ok"):
            return {"ok": False, "error": "db_persistence_failed"}

        return {"ok": True, "data": persisted}

    def _to_credit_days(self, value) -> int:
        try:
            days = int(value)
            return days if days >= 0 else _DEFAULT_CREDIT_DAYS
        except (TypeError, ValueError):
            return _DEFAULT_CREDIT_DAYS

    def _add_days(self, date_str: str | None, days: int) -> str | None:
        if not date_str:
            return None
        try:
            return (date.fromisoformat(date_str) + timedelta(days=days)).isoformat()
        except ValueError:
            return None

    def _folio_from_trip(self, trip_folio: str) -> str:
        match = re.search(r"(\d+)$", trip_folio or "")
        n = match.group(1) if match else "0000"
        return f"R-{n}"

    def _payment_status(self, total: float, paid: float) -> str:
        if total > 0 and paid >= total:
            return "paid"
        if paid > 0:
            return "partial"
        return "receivable"

    def _collection_status(self, total: float, paid: float, due_date: str | None, today: str) -> str:
        if total > 0 and paid >= total:
            return "paid"
        balance = max(0.0, total - paid)
        if balance > 0 and due_date and due_date < today:
            return "overdue"
        if paid > 0:
            return "partial"
        return "pending"
