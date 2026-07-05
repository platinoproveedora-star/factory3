from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_DEFAULT_WARNING_PCT = -10.0
_DEFAULT_ALERT_PCT = -20.0
_MIN_BASELINE_PERIODS = 3


class MileageCalculateService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        unit_key = str(context.get("unit_key") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not unit_key:
            return {"ok": False, "error": "missing_required_fields"}

        period = context.get("period") if isinstance(context.get("period"), dict) else {}
        period_from = period.get("from")
        period_to = period.get("to")

        db = SupabaseClient({**context, "schema": _SCHEMA})

        unit_res = db.rest_select(
            "units", filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"}, select="unit_key", limit=1
        )
        if not unit_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": unit_res.get("error")}}
        if not unit_res.get("data"):
            return {"ok": False, "error": "unit_not_found"}

        loads_res = db.rest_select(
            "fuel_loads",
            filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"},
            select="load_date,liters,odometer_km",
        )
        if not loads_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": loads_res.get("error")}}
        all_loads = loads_res.get("data") or []

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

        loads = sorted(
            (l for l in all_loads if in_period(l.get("load_date"))),
            key=lambda l: l.get("load_date") or "",
        )
        with_odometer = [l for l in loads if l.get("odometer_km") is not None]
        if len(with_odometer) < 2:
            return {"ok": False, "error": "insufficient_data"}

        km_traveled = float(with_odometer[-1]["odometer_km"]) - float(with_odometer[0]["odometer_km"])
        liters_loaded = sum(float(l.get("liters") or 0) for l in loads)
        km_per_liter = round(km_traveled / liters_loaded, 3) if liters_loaded > 0 else 0.0

        expected = self._to_amount(context.get("expected_km_per_liter"))
        warnings: list[str] = []
        if expected is None:
            expected, baseline_ok = self._historical_baseline(db, empresa_id, unit_key, period_from)
            if not baseline_ok:
                warnings.append("no_baseline")

        alert_threshold = self._to_amount(context.get("alert_threshold_pct")) or _DEFAULT_ALERT_PCT
        warning_threshold = self._to_amount(context.get("warning_threshold_pct")) or _DEFAULT_WARNING_PCT

        if expected and expected > 0:
            deviation_pct = round(((km_per_liter - expected) / expected) * 100, 2)
            if deviation_pct < alert_threshold:
                flag = "alert"
            elif deviation_pct < warning_threshold:
                flag = "warning"
            else:
                flag = "ok"
        else:
            deviation_pct = None
            flag = "ok"

        report = {
            "empresa_id": empresa_id,
            "unit_key": unit_key,
            "period_from": period_from,
            "period_to": period_to,
            "km_traveled": km_traveled,
            "liters_loaded": liters_loaded,
            "km_per_liter": km_per_liter,
            "expected_km_per_liter": expected,
            "deviation_pct": deviation_pct,
            "flag": flag,
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se persistio", "data": {"efficiency": report, "warnings": warnings}}

        res = db.rest_upsert("fuel_efficiency", report, "empresa_id,unit_key,period_from,period_to")
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        persisted = (res.get("data") or [report])[0]
        return {"ok": True, "data": {"efficiency": persisted, "warnings": warnings}}

    def _historical_baseline(self, db: SupabaseClient, empresa_id: str, unit_key: str, before_period: str | None) -> tuple[float | None, bool]:
        res = db.rest_select(
            "fuel_efficiency",
            filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"},
            select="period_from,km_per_liter",
            order="period_from.desc",
        )
        if not res.get("ok"):
            return None, False
        rows = res.get("data") or []
        if before_period:
            rows = [r for r in rows if (r.get("period_from") or "") < before_period]
        if len(rows) < _MIN_BASELINE_PERIODS:
            return None, False
        values = [float(r.get("km_per_liter") or 0) for r in rows]
        return round(sum(values) / len(values), 3), True

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
