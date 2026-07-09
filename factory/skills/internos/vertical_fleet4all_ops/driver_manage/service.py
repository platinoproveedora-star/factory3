from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


class DriverManageService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        driver_key = str(context.get("driver_key") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not driver_key:
            return {"ok": False, "error": "driver_key_requerido"}

        if context.get("baja"):
            return self._baja(context, empresa_id, driver_key)

        row = {
            "empresa_id": empresa_id,
            "driver_key": driver_key,
            "full_name": self._blank_to_none(context.get("full_name")),
            "phone": self._blank_to_none(context.get("phone")),
            "license_number": self._blank_to_none(context.get("license_number")),
            "pay_scheme": str(context.get("pay_scheme") or "commission").strip() or "commission",
            "pay_rate": self._to_amount(context.get("pay_rate")) or 0,
            "status": str(context.get("status") or "active").strip() or "active",
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en fleet4all.drivers", "data": {"driver": row}}

        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})
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
