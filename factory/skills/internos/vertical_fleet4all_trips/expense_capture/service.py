from __future__ import annotations

import re
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_FOLIO_PREFIX = "G-"

_EXPENSE_KEYWORDS = {
    "fuel": ["gasolina", "diesel", "fuel", "combustible", "gas"],
    "tolls": ["caseta", "peaje", "toll", "cuota"],
    "food": ["comida", "food", "alimento", "restaurante", "desayuno"],
    "repair": ["taller", "reparacion", "repair", "refaccion", "llanta", "mecanico"],
}


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class ExpenseCaptureService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        image_b64 = context.get("image_base64")
        if image_b64 and not context.get("confirmed"):
            return self._draft_from_image(image_b64, context.get("media_type") or "image/jpeg")

        fields = self._resolve_fields(context)
        amount = self._to_amount(fields.get("amount"))
        if amount is None or amount <= 0:
            return {"ok": False, "error": "invalid_amount"}

        concept = str(fields.get("concept") or "").strip()
        expense_type = str(context.get("expense_type") or "").strip().lower() or self._infer_expense_type(concept)
        trip_folio = str(context.get("trip_folio") or fields.get("trip_folio") or "").strip() or None

        base = {
            "empresa_id": empresa_id,
            "trip_folio": trip_folio,
            "amount": amount,
            "concept": concept,
            "expense_type": expense_type,
            "expense_date": fields.get("expense_date"),
            "driver_key": context.get("driver_key"),
            "doc_id": context.get("doc_id"),
        }

        dry_run = context.get("dry_run", True)
        if not dry_run and trip_folio:
            check = self._check_trip_active(context, empresa_id, trip_folio)
            if not check.get("ok"):
                return check

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all.expenses",
                "data": {"expense": {**base, "expense_folio": None}, "warnings": ["dry_run: folio no asignado"]},
            }

        db = SupabaseClient({**context, "schema": _SCHEMA})
        folio = self._next_folio(db, empresa_id)
        row = {**base, "expense_folio": folio}
        res = db.rest_insert("expenses", row)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}

        created = (res.get("data") or [row])[0]
        return {"ok": True, "data": {"expense": created, "warnings": []}}

    def _draft_from_image(self, image_b64: str, media_type: str) -> dict:
        result = _runner().run(
            "vertical_factory_utils/ai_interpreter",
            {
                "mode": "extract",
                "content_b64": image_b64,
                "media_type": media_type,
                "schema": {"amount": None, "concept": None, "expense_date": None},
                "context": "Extrae los datos de un ticket/comprobante de gasto de flotilla.",
            },
        )
        if not result.get("ok"):
            return {"ok": False, "error": "ai_response_not_parseable", "data": {"detail": result.get("error")}}
        extracted = (result.get("data") or {}).get("extracted") or {}
        return {
            "ok": True,
            "message": "draft: confirma los datos para persistir (context.confirmed=true)",
            "data": {"expense_draft": extracted, "warnings": ["pendiente de confirmacion"]},
        }

    def _resolve_fields(self, context: dict) -> dict:
        text = str(context.get("text") or "").strip()
        if text:
            return self._parse_text(text)
        return {
            "amount": context.get("amount"),
            "concept": context.get("concept"),
            "expense_date": context.get("expense_date"),
        }

    def _parse_text(self, text: str) -> dict:
        parts = [p.strip() for p in text.split(",")]
        amount = parts[0] if len(parts) > 0 else None
        concept = parts[1] if len(parts) > 1 else ""
        expense_date = self._parse_date_ddmmyy(parts[2]) if len(parts) > 2 else None
        trip_folio = parts[3] if len(parts) > 3 else None
        return {"amount": amount, "concept": concept, "expense_date": expense_date, "trip_folio": trip_folio}

    def _parse_date_ddmmyy(self, raw: str) -> str | None:
        try:
            d, m, y = raw.split("/")
            yy = int(y)
            year = 2000 + yy if yy < 100 else yy
            return f"{year:04d}-{int(m):02d}-{int(d):02d}"
        except Exception:
            return None

    def _infer_expense_type(self, concept: str) -> str:
        text = concept.lower()
        for expense_type, keywords in _EXPENSE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return expense_type
        return "other"

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _check_trip_active(self, context: dict, empresa_id: str, trip_folio: str) -> dict:
        db = SupabaseClient({**context, "schema": _SCHEMA})
        res = db.rest_select(
            "trips",
            filters={"empresa_id": f"eq.{empresa_id}", "trip_folio": f"eq.{trip_folio}"},
            select="trip_status",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        if not rows:
            return {"ok": False, "error": "trip_not_found"}
        if rows[0].get("trip_status") != "active":
            return {"ok": False, "error": "trip_not_active"}
        return {"ok": True}

    def _next_folio(self, db: SupabaseClient, empresa_id: str) -> str:
        res = db.rest_select(
            "expenses",
            filters={"empresa_id": f"eq.{empresa_id}", "expense_folio": f"like.{_FOLIO_PREFIX}*"},
            select="expense_folio",
            order="expense_folio.desc",
            limit=1,
        )
        rows = (res.get("data") or []) if res.get("ok") else []
        last_n = 0
        if rows:
            match = re.search(r"(\d+)$", str(rows[0].get("expense_folio") or ""))
            if match:
                last_n = int(match.group(1))
        return f"{_FOLIO_PREFIX}{last_n + 1:04d}"
