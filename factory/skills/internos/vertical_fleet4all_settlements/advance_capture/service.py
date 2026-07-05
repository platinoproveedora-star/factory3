from __future__ import annotations

import re

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "A-"


class AdvanceCaptureService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        driver_key = str(context.get("driver_key") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not driver_key:
            return {"ok": False, "error": "missing_required_fields"}

        amount = self._to_amount(context.get("amount"))
        if amount is None or amount <= 0:
            return {"ok": False, "error": "invalid_amount"}

        base = {
            "empresa_id": empresa_id,
            "driver_key": driver_key,
            "amount": amount,
            "advance_date": context.get("advance_date"),
            "concept": context.get("concept"),
            "trip_folio": context.get("trip_folio"),
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.driver_advances",
                "data": {
                    "advance": {**base, "advance_folio": None, "settled_in": None},
                    "warnings": ["dry_run: folio no asignado"],
                },
            }

        db = SupabaseClient({**context, "schema": _SCHEMA})
        folio = self._next_folio(db, empresa_id)
        row = {**base, "advance_folio": folio, "settled_in": None}
        res = db.rest_insert("driver_advances", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}

        created = (res.get("data") or [row])[0]
        return {"ok": True, "data": {"advance": created, "warnings": []}}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "driver_advances",
            filters={"empresa_id": f"eq.{empresa_id}", "advance_folio": f"like.{_FOLIO_PREFIX}*"},
            select="advance_folio",
            order="advance_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("advance_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
