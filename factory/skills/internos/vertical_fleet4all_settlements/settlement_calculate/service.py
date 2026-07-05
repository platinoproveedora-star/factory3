from __future__ import annotations

import re

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "S-"


class SettlementCalculateService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        driver_key = str(context.get("driver_key") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not driver_key:
            return {"ok": False, "error": "missing_required_fields"}

        period = context.get("period") if isinstance(context.get("period"), dict) else {}
        period_from = period.get("from")
        period_to = period.get("to")
        currency = str(context.get("currency") or "MXN").strip().upper()

        db = SupabaseClient({**context, "schema": _SCHEMA})

        driver_res = db.rest_select(
            "drivers",
            filters={"empresa_id": f"eq.{empresa_id}", "driver_key": f"eq.{driver_key}"},
            select="*",
            limit=1,
        )
        if not driver_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": driver_res.get("error")}}
        drivers = driver_res.get("data") or []
        if not drivers:
            return {"ok": False, "error": "driver_not_found"}
        driver = drivers[0]
        pay_scheme = driver.get("pay_scheme") or "per_trip"
        pay_rate = float(driver.get("pay_rate") or 0)

        settlements_res = db.rest_select(
            "settlements",
            filters={"empresa_id": f"eq.{empresa_id}", "driver_key": f"eq.{driver_key}"},
            select="*",
        )
        if not settlements_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": settlements_res.get("error")}}
        existing_settlements = settlements_res.get("data") or []

        existing_for_period = next(
            (
                s for s in existing_settlements
                if s.get("period_from") == period_from and s.get("period_to") == period_to
            ),
            None,
        )
        if existing_for_period and existing_for_period.get("status") != "draft":
            return {"ok": False, "error": "already_settled"}

        already_settled_trips: set[str] = set()
        for s in existing_settlements:
            if existing_for_period and s.get("settlement_folio") == existing_for_period.get("settlement_folio"):
                continue
            for folio in (s.get("trips_included") or []):
                already_settled_trips.add(folio)

        trips_res = db.rest_select(
            "trips",
            filters={
                "empresa_id": f"eq.{empresa_id}",
                "driver_key": f"eq.{driver_key}",
                "trip_status": "eq.closed",
            },
            select="trip_folio,departure_date,trip_profit",
        )
        if not trips_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": trips_res.get("error")}}
        all_trips = trips_res.get("data") or []

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

        trips = [
            t for t in all_trips
            if in_period(t.get("departure_date")) and t.get("trip_folio") not in already_settled_trips
        ]

        if pay_scheme in ("per_trip", "percent") and not trips:
            return {"ok": False, "error": "no_trips_in_period"}

        if pay_scheme == "per_trip":
            gross_amount = pay_rate * len(trips)
        elif pay_scheme == "percent":
            gross_amount = (pay_rate / 100.0) * sum(float(t.get("trip_profit") or 0) for t in trips)
        else:
            gross_amount = pay_rate

        advances_res = db.rest_select(
            "driver_advances",
            filters={"empresa_id": f"eq.{empresa_id}", "driver_key": f"eq.{driver_key}", "settled_in": "is.null"},
            select="advance_folio,amount",
        )
        if not advances_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": advances_res.get("error")}}
        pending_advances = advances_res.get("data") or []
        advances_deducted = sum(float(a.get("amount") or 0) for a in pending_advances)

        other_deductions = self._to_amount(context.get("other_deductions")) or 0.0
        net_amount = gross_amount - advances_deducted - other_deductions

        settlement_folio = (
            existing_for_period.get("settlement_folio") if existing_for_period else self._next_folio(db, empresa_id)
        )

        settlement = {
            "empresa_id": empresa_id,
            "settlement_folio": settlement_folio,
            "driver_key": driver_key,
            "period_from": period_from,
            "period_to": period_to,
            "trips_included": [t.get("trip_folio") for t in trips],
            "gross_amount": gross_amount,
            "advances_deducted": advances_deducted,
            "other_deductions": other_deductions,
            "net_amount": net_amount,
            "currency": currency,
            "status": "draft",
            "receipt_pdf_path": existing_for_period.get("receipt_pdf_path") if existing_for_period else None,
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se persistio",
                "data": {"settlement": settlement, "warnings": ["dry_run: no se persistio"]},
            }

        if existing_for_period:
            upd = db.rest_update(
                "settlements", values=settlement,
                filters={"empresa_id": f"eq.{empresa_id}", "settlement_folio": f"eq.{settlement_folio}"},
            )
            if not upd.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}
            persisted = (upd.get("data") or [settlement])[0]
        else:
            ins = db.rest_insert("settlements", settlement)
            if not ins.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": ins.get("error")}}
            persisted = (ins.get("data") or [settlement])[0]

        if context.get("approve"):
            approved = self._approve(db, empresa_id, settlement_folio, pending_advances)
            if not approved.get("ok"):
                return approved
            persisted = approved["data"]

        return {"ok": True, "data": {"settlement": persisted, "warnings": []}}

    def _approve(self, db: SupabaseClient, empresa_id: str, settlement_folio: str, pending_advances: list) -> dict:
        for advance in pending_advances:
            upd = db.rest_update(
                "driver_advances",
                values={"settled_in": settlement_folio},
                filters={"empresa_id": f"eq.{empresa_id}", "advance_folio": f"eq.{advance.get('advance_folio')}"},
            )
            if not upd.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}

        status_upd = db.rest_update(
            "settlements",
            values={"status": "approved"},
            filters={"empresa_id": f"eq.{empresa_id}", "settlement_folio": f"eq.{settlement_folio}"},
        )
        if not status_upd.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": status_upd.get("error")}}
        return {"ok": True, "data": (status_upd.get("data") or [{}])[0]}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "settlements",
            filters={"empresa_id": f"eq.{empresa_id}", "settlement_folio": f"like.{_FOLIO_PREFIX}*"},
            select="settlement_folio",
            order="settlement_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("settlement_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
