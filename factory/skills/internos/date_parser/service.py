"""Service for date_parser - parses simple relative dates."""

from __future__ import annotations

from datetime import date, datetime, timedelta


class DateParserService:

    def ejecutar(self, context: dict) -> dict:
        text = str(context.get("text", "")).strip().lower()
        base_raw = context.get("base_date")
        base = self._parse_iso(base_raw).date() if base_raw else date.today()
        if not text:
            return {"ok": False, "error": "text es requerido"}
        mapping = {
            "hoy": base,
            "today": base,
            "mañana": base + timedelta(days=1),
            "manana": base + timedelta(days=1),
            "tomorrow": base + timedelta(days=1),
            "ayer": base - timedelta(days=1),
            "yesterday": base - timedelta(days=1),
        }
        if text in mapping:
            parsed = mapping[text]
        else:
            try:
                parsed = self._parse_iso(text).date()
            except ValueError:
                return {"ok": False, "error": "fecha no reconocida; usa hoy, mañana, ayer o YYYY-MM-DD"}
        return {"ok": True, "data": {"date": parsed.isoformat(), "base_date": base.isoformat()}}

    def _parse_iso(self, value: object) -> datetime:
        if not isinstance(value, str):
            raise ValueError("invalid date")
        return datetime.fromisoformat(value.strip())
