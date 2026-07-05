from __future__ import annotations

import re
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "P-"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class PaymentCaptureService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        trip_folio = str(context.get("trip_folio") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not trip_folio:
            return {"ok": False, "error": "missing_required_fields"}

        amount = self._to_amount(context.get("amount"))
        if amount is None or amount <= 0:
            return {"ok": False, "error": "invalid_amount"}

        method = str(context.get("method") or "transfer").strip().lower()
        base = {
            "empresa_id": empresa_id,
            "trip_folio": trip_folio,
            "amount": amount,
            "payment_date": context.get("payment_date"),
            "method": method,
            "tracking_key": context.get("tracking_key"),
            "notes": context.get("notes"),
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.payments",
                "data": {"payment": {**base, "payment_folio": None}, "warnings": ["dry_run: folio no asignado"]},
            }

        db = SupabaseClient({**context, "schema": _SCHEMA})

        trip_res = db.rest_select(
            "trips", filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="trip_folio", limit=1,
        )
        if not trip_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": trip_res.get("error")}}
        if not trip_res.get("data"):
            return {"ok": False, "error": "trip_not_found"}

        folio = self._next_folio(db, empresa_id)
        row = {**base, "payment_folio": folio}
        res = db.rest_insert("payments", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        created = (res.get("data") or [row])[0]

        warnings = []
        sync = _runner().run(
            "vertical_fleet4all_collections/receivables_sync",
            {**context, "empresa_id": empresa_id, "trip_folio": trip_folio, "dry_run": False},
        )
        if not sync.get("ok"):
            warnings.append(f"receivables_sync_failed: {sync.get('error')}")

        return {"ok": True, "data": {"payment": created, "warnings": warnings}}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "payments",
            filters={"empresa_id": f"eq.{empresa_id}", "payment_folio": f"like.{_FOLIO_PREFIX}*"},
            select="payment_folio",
            order="payment_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("payment_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
