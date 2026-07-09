from __future__ import annotations

import re

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "DRV-"


class DriverManageService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        driver_key = str(context.get("driver_key") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        if context.get("baja"):
            if not driver_key:
                return {"ok": False, "error": "driver_key_requerido"}
            return self._baja(context, empresa_id, driver_key)

        is_new = not driver_key
        dry_run = context.get("dry_run", True)

        row = {
            "empresa_id": empresa_id,
            "driver_key": driver_key or None,
            "full_name": self._blank_to_none(context.get("full_name")),
            "phone": self._blank_to_none(context.get("phone")),
            "license_number": self._blank_to_none(context.get("license_number")),
            "pay_scheme": str(context.get("pay_scheme") or "commission").strip() or "commission",
            "pay_rate": self._to_amount(context.get("pay_rate")) or 0,
            "status": str(context.get("status") or "active").strip() or "active",
        }

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.drivers",
                "data": {"driver": row, "warnings": ["dry_run: driver_key no asignado"] if is_new else []},
            }

        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})

        if is_new:
            driver_key = self._next_folio(db, empresa_id)
            row["driver_key"] = driver_key
            res = db.rest_insert("drivers", row)
        else:
            existing = db.rest_select(
                "drivers",
                filters={"empresa_id": f"eq.{empresa_id}", "driver_key": f"eq.{driver_key}"},
                select="driver_key",
                limit=1,
            )
            if not existing.get("ok"):
                return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}
            if existing.get("data"):
                res = db.rest_update("drivers", row, {"empresa_id": f"eq.{empresa_id}", "driver_key": f"eq.{driver_key}"})
            else:
                res = db.rest_insert("drivers", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"driver": (res.get("data") or [row])[0], "warnings": []}}

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        # No se puede usar order+limit=1: claves manuales viejas sin sufijo
        # numerico (ej. "DRV-DEMO") ordenan como texto antes que "DRV-0001"
        # y rompen el calculo. Se revisan todas y se toma el maximo numerico.
        res = db.rest_select(
            "drivers",
            filters={"empresa_id": f"eq.{empresa_id}", "driver_key": f"like.{_FOLIO_PREFIX}*"},
            select="driver_key",
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        for row in rows:
            match = re.search(r"(\d+)$", str(row.get("driver_key") or ""))
            if match:
                last_n = max(last_n, int(match.group(1)))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"

    def _baja(self, context: dict, empresa_id: str, driver_key: str) -> dict:
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se dio de baja",
                "data": {"driver": {"driver_key": driver_key, "status": "inactive"}},
            }

        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})
        existing = db.rest_select(
            "drivers",
            filters={"empresa_id": f"eq.{empresa_id}", "driver_key": f"eq.{driver_key}"},
            select="driver_key",
            limit=1,
        )
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}
        if not existing.get("data"):
            return {"ok": False, "error": "driver_not_found"}

        res = db.rest_update("drivers", {"status": "inactive"}, {"empresa_id": f"eq.{empresa_id}", "driver_key": f"eq.{driver_key}"})
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"driver": (res.get("data") or [{}])[0], "warnings": []}}

    def _blank_to_none(self, value):
        text = str(value or "").strip()
        return text or None

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
