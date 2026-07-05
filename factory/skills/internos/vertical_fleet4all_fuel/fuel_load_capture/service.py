from __future__ import annotations

import re
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "F-"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class FuelLoadCaptureService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        unit_key = str(context.get("unit_key") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not unit_key:
            return {"ok": False, "error": "missing_required_fields"}

        image_b64 = context.get("image_base64")
        if image_b64 and not context.get("confirmed"):
            return self._draft_from_image(image_b64, context.get("media_type") or "image/jpeg")

        fields = self._resolve_fields(context)
        liters = self._to_amount(fields.get("liters"))
        amount = self._to_amount(fields.get("amount"))
        if liters is None or liters <= 0 or amount is None or amount <= 0:
            return {"ok": False, "error": "invalid_amount"}
        price_per_liter = round(amount / liters, 3) if liters > 0 else 0.0

        odometer_km = self._to_amount(context.get("odometer_km") or fields.get("odometer_km"))
        base = {
            "empresa_id": empresa_id,
            "unit_key": unit_key,
            "driver_key": context.get("driver_key"),
            "trip_folio": context.get("trip_folio"),
            "load_date": fields.get("load_date") or context.get("load_date"),
            "liters": liters,
            "amount": amount,
            "currency": str(context.get("currency") or "MXN").strip().upper(),
            "price_per_liter": price_per_liter,
            "odometer_km": odometer_km,
            "station": fields.get("station") or context.get("station"),
            "doc_id": context.get("doc_id"),
        }

        warnings: list[str] = []
        dry_run = context.get("dry_run", True)

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.fuel_loads",
                "data": {"fuel_load": {**base, "fuel_folio": None}, "warnings": warnings + ["dry_run: folio no asignado"]},
            }

        db = SupabaseClient({**context, "schema": _SCHEMA})

        if odometer_km is not None:
            unit_res = db.rest_select("units", filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"}, select="odometer_km", limit=1)
            if not unit_res.get("ok"):
                return {"ok": False, "error": "db_persistence_failed", "data": {"detail": unit_res.get("error")}}
            units = unit_res.get("data") or []
            if not units:
                return {"ok": False, "error": "unit_not_found"}
            current_odometer = float(units[0].get("odometer_km") or 0)
            if odometer_km > current_odometer:
                db.rest_update("units", values={"odometer_km": odometer_km}, filters={"empresa_id": f"eq.{empresa_id}", "unit_key": f"eq.{unit_key}"})
            else:
                warnings.append("odometer_lower")

        folio = self._next_folio(db, empresa_id)
        row = {**base, "fuel_folio": folio}
        res = db.rest_insert("fuel_loads", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        created = (res.get("data") or [row])[0]

        if context.get("as_expense"):
            expense_res = _runner().run(
                "vertical_fleet4all_trips/expense_capture",
                {
                    "empresa_id": empresa_id,
                    "amount": amount,
                    "concept": f"fuel {unit_key}",
                    "expense_type": "fuel",
                    "expense_date": base["load_date"],
                    "trip_folio": base["trip_folio"],
                    "driver_key": base["driver_key"],
                    "dry_run": False,
                },
            )
            if not expense_res.get("ok"):
                warnings.append(f"as_expense_failed: {expense_res.get('error')}")

        return {"ok": True, "data": {"fuel_load": created, "warnings": warnings}}

    def _draft_from_image(self, image_b64: str, media_type: str) -> dict:
        result = _runner().run(
            "vertical_factory_utils/ai_interpreter",
            {
                "mode": "extract",
                "content_b64": image_b64,
                "media_type": media_type,
                "schema": {"liters": None, "amount": None, "load_date": None, "station": None},
                "context": "Extrae los datos de un ticket de carga de combustible.",
            },
        )
        if not result.get("ok"):
            return {"ok": False, "error": "ai_response_not_parseable", "data": {"detail": result.get("error")}}
        extracted = (result.get("data") or {}).get("extracted") or {}
        return {
            "ok": True,
            "message": "draft: confirma los datos para persistir (context.confirmed=true)",
            "data": {"fuel_load_draft": extracted, "warnings": ["pendiente de confirmacion"]},
        }

    def _resolve_fields(self, context: dict) -> dict:
        text = str(context.get("text") or "").strip()
        if text:
            return self._parse_text(text)
        return {
            "liters": context.get("liters"),
            "amount": context.get("amount"),
            "load_date": context.get("load_date"),
            "station": context.get("station"),
        }

    def _parse_text(self, text: str) -> dict:
        parts = [p.strip() for p in text.split(",")]
        liters = parts[0] if len(parts) > 0 else None
        amount = parts[1] if len(parts) > 1 else None
        load_date = self._parse_date_ddmmyy(parts[2]) if len(parts) > 2 else None
        station = parts[3] if len(parts) > 3 else None
        return {"liters": liters, "amount": amount, "load_date": load_date, "station": station}

    def _parse_date_ddmmyy(self, raw: str) -> str | None:
        try:
            d, m, y = raw.split("/")
            yy = int(y)
            year = 2000 + yy if yy < 100 else yy
            return f"{year:04d}-{int(m):02d}-{int(d):02d}"
        except Exception:
            return None

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "fuel_loads",
            filters={"empresa_id": f"eq.{empresa_id}", "fuel_folio": f"like.{_FOLIO_PREFIX}*"},
            select="fuel_folio",
            order="fuel_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("fuel_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
