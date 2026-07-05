from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "Q-"


def normalize(value: str) -> str:
    text = str(value or "").strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return text


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class QuoteBuildService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        customer = str(context.get("customer") or "").strip()
        origin = normalize(context.get("origin"))
        destination = normalize(context.get("destination"))
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not customer or not origin or not destination:
            return {"ok": False, "error": "missing_required_fields"}

        cargo_type = normalize(context.get("cargo_type")) or "general"
        weight_tons = self._to_amount(context.get("weight_tons")) or 0.0
        distance_km = self._to_amount(context.get("distance_km"))
        currency = str(context.get("currency") or "MXN").strip().upper()

        db = SupabaseClient({**context, "schema": _SCHEMA})

        rate_res = db.rest_select(
            "rates",
            filters={"empresa_id": f"eq.{empresa_id}", "origin": f"eq.{origin}", "destination": f"eq.{destination}", "cargo_type": f"eq.{cargo_type}"},
            select="*", limit=1,
        )
        if not rate_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": rate_res.get("error")}}
        rate_matches = rate_res.get("data") or []

        if not rate_matches:
            fallback_res = db.rest_select(
                "rates", filters={"empresa_id": f"eq.{empresa_id}", "origin": f"eq.{origin}", "destination": f"eq.{destination}"},
                select="*", limit=1,
            )
            if not fallback_res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": fallback_res.get("error")}}
            rate_matches = fallback_res.get("data") or []

        if not rate_matches:
            nearby_res = db.rest_select("rates", filters={"empresa_id": f"eq.{empresa_id}", "origin": f"eq.{origin}"}, select="rate_key,origin,destination,cargo_type")
            nearby = nearby_res.get("data") or [] if nearby_res.get("ok") else []
            return {"ok": False, "error": "no_rate_found", "data": {"warnings": nearby}}

        rate = rate_matches[0]
        base_price = float(rate.get("base_price") or 0)
        price_per_km = float(rate.get("price_per_km") or 0)
        price_per_ton = float(rate.get("price_per_ton") or 0)
        quoted_price = base_price + (distance_km or 0) * price_per_km + weight_tons * price_per_ton

        valid_days = int(context.get("valid_days") or 7)
        valid_until = (date.today() + timedelta(days=valid_days)).isoformat()
        status = "sent" if context.get("mark_sent") else "draft"

        base = {
            "empresa_id": empresa_id,
            "customer": customer,
            "origin": origin,
            "destination": destination,
            "cargo_type": cargo_type,
            "weight_tons": weight_tons,
            "distance_km": distance_km,
            "quoted_price": round(quoted_price, 2),
            "currency": currency,
            "valid_until": valid_until,
            "status": status,
            "trip_folio": None,
            "pdf_path": None,
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.quotes",
                "data": {"quote": {**base, "quote_folio": None}, "warnings": ["dry_run: folio no asignado"]},
            }

        folio = self._next_folio(db, empresa_id)
        row = {**base, "quote_folio": folio}
        res = db.rest_insert("quotes", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        created = (res.get("data") or [row])[0]

        warnings: list[str] = []
        if context.get("accept"):
            trip_res = _runner().run(
                "vertical_fleet4all_trips/trip_create",
                {
                    "empresa_id": empresa_id, "customer": customer, "origin": origin, "destination": destination,
                    "sale_price": created["quoted_price"], "currency": currency, "driver_key": context.get("driver_key"),
                    "unit_key": context.get("unit_key"), "dry_run": False,
                },
            )
            if trip_res.get("ok"):
                trip_folio = (trip_res.get("data") or {}).get("trip", {}).get("trip_folio")
                upd = db.rest_update(
                    "quotes", values={"trip_folio": trip_folio, "status": "accepted"},
                    filters={"empresa_id": f"eq.{empresa_id}", "quote_folio": f"eq.{folio}"},
                )
                created = (upd.get("data") or [{**created, "trip_folio": trip_folio, "status": "accepted"}])[0] if upd.get("ok") else created
                if not upd.get("ok"):
                    warnings.append(f"link_trip_failed: {upd.get('error')}")
            else:
                warnings.append(f"trip_create_failed: {trip_res.get('error')}")

        return {"ok": True, "data": {"quote": created, "warnings": warnings}}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "quotes",
            filters={"empresa_id": f"eq.{empresa_id}", "quote_folio": f"like.{_FOLIO_PREFIX}*"},
            select="quote_folio",
            order="quote_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("quote_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
