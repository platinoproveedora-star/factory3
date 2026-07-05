from __future__ import annotations

import unicodedata

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


def normalize(value: str) -> str:
    text = str(value or "").strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return text


class RateManageService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        action = str(context.get("action") or "create").strip().lower()
        if action == "list":
            return self._list(context, empresa_id)
        return self._create(context, empresa_id)

    def _create(self, context: dict, empresa_id: str) -> dict:
        origin = normalize(context.get("origin"))
        destination = normalize(context.get("destination"))
        cargo_type = normalize(context.get("cargo_type")) or "general"
        if not origin or not destination:
            return {"ok": False, "error": "missing_required_fields"}

        rate_key = f"{origin.replace(' ', '-')}__{destination.replace(' ', '-')}__{cargo_type.replace(' ', '-')}"
        base = {
            "empresa_id": empresa_id,
            "rate_key": rate_key,
            "origin": origin,
            "destination": destination,
            "cargo_type": cargo_type,
            "unit_type": context.get("unit_type"),
            "base_price": self._to_amount(context.get("base_price")) or 0.0,
            "price_per_km": self._to_amount(context.get("price_per_km")) or 0.0,
            "price_per_ton": self._to_amount(context.get("price_per_ton")) or 0.0,
            "currency": str(context.get("currency") or "MXN").strip().upper(),
            "status": "active",
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en fleet4all.rates", "data": {"rate": base, "warnings": []}}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        existing_res = db.rest_select("rates", filters={"empresa_id": f"eq.{empresa_id}", "rate_key": f"eq.{rate_key}"}, select="rate_key", limit=1)
        if not existing_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": existing_res.get("error")}}
        if existing_res.get("data"):
            return {"ok": False, "error": "rate_exists"}

        res = db.rest_insert("rates", base)
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        created = (res.get("data") or [base])[0]
        return {"ok": True, "data": {"rate": created, "warnings": []}}

    def _list(self, context: dict, empresa_id: str) -> dict:
        db = SupabaseClient({**context, "schema": _SCHEMA})
        filters = {"empresa_id": f"eq.{empresa_id}"}
        if context.get("origin"):
            filters["origin"] = f"eq.{normalize(context['origin'])}"
        if context.get("destination"):
            filters["destination"] = f"eq.{normalize(context['destination'])}"
        res = db.rest_select("rates", filters=filters, select="*")
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"rates": res.get("data") or [], "warnings": []}}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
