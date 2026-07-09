from __future__ import annotations

import re

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "UN-"


class UnitManageService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        unit_key = str(context.get("unit_key") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        if context.get("baja"):
            if not unit_key:
                return {"ok": False, "error": "unit_key_requerido"}
            return self._baja(context, empresa_id, unit_key)

        is_new = not unit_key
        dry_run = context.get("dry_run", True)

        row = {
            "empresa_id": empresa_id,
            "unit_key": unit_key or None,
            "plate": self._blank_to_none(context.get("plate")),
            "brand": self._blank_to_none(context.get("brand")),
            "model": self._blank_to_none(context.get("model")),
            "year": self._to_int(context.get("year")),
            "unit_type": str(context.get("unit_type") or "tractor").strip() or "tractor",
            "odometer_km": self._to_amount(context.get("odometer_km")) or 0,
            "status": str(context.get("status") or "active").strip() or "active",
        }

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.units",
                "data": {"unit": row, "warnings": ["dry_run: unit_key no asignado"] if is_new else []},
            }

        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})

        if is_new:
            unit_key = self._next_folio(db, empresa_id)
            row["unit_key"] = unit_key
            res = db.rest_insert("units", row)
        else:
            existing = db.rest_select(
                "units",
                filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"},
                select="unit_key",
                limit=1,
            )
            if not existing.get("ok"):
                return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}
            if existing.get("data"):
                res = db.rest_update("units", row, {"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"})
            else:
                res = db.rest_insert("units", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"unit": (res.get("data") or [row])[0], "warnings": []}}

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        # No se puede usar order+limit=1: claves manuales viejas sin sufijo
        # numerico ordenan como texto antes que "UN-0001" y rompen el calculo.
        # Se revisan todas y se toma el maximo numerico.
        res = db.rest_select(
            "units",
            filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"like.{_FOLIO_PREFIX}*"},
            select="unit_key",
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        for row in rows:
            match = re.search(r"(\d+)$", str(row.get("unit_key") or ""))
            if match:
                last_n = max(last_n, int(match.group(1)))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"

    def _baja(self, context: dict, empresa_id: str, unit_key: str) -> dict:
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se dio de baja",
                "data": {"unit": {"unit_key": unit_key, "status": "inactive"}},
            }

        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})
        existing = db.rest_select(
            "units",
            filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"},
            select="unit_key",
            limit=1,
        )
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}
        if not existing.get("data"):
            return {"ok": False, "error": "unit_not_found"}

        res = db.rest_update("units", {"status": "inactive"}, {"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"})
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"unit": (res.get("data") or [{}])[0], "warnings": []}}

    def _blank_to_none(self, value):
        text = str(value or "").strip()
        return text or None

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
