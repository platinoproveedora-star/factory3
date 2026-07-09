from __future__ import annotations

from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class PaymentManageService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        action = str(context.get("action") or "").strip().lower()
        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})

        if action == "update":
            return self._update(db, context, empresa_id)
        if action == "cancel":
            return self._cancel(db, context, empresa_id)
        return {"ok": False, "error": "action_invalida"}

    def _update(self, db: SupabaseClient, context: dict, empresa_id: str) -> dict:
        payment_folio = str(context.get("payment_folio") or "").strip()
        if not payment_folio:
            return {"ok": False, "error": "payment_folio_requerido"}

        values: dict = {}
        for field in ("payment_date", "method", "notes"):
            if field in context:
                raw = context.get(field)
                values[field] = str(raw).strip() or None if raw is not None else None
        if "amount" in context:
            amount = self._to_amount(context.get("amount"))
            if amount is None or amount <= 0:
                return {"ok": False, "error": "invalid_amount"}
            values["amount"] = amount
        if not values:
            return {"ok": False, "error": "sin_campos_para_actualizar"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo fleet4all.payments", "data": {"payment": {"payment_folio": payment_folio, **values}}}

        res = db.rest_update("payments", values=values, filters={"empresa_id": f"eq.{empresa_id}", "payment_folio": f"eq.{payment_folio}"})
        if not res.get("ok"):
            return {"ok": False, "error": "db_update_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "payment_not_found"}

        warnings = self._resync(rows[0].get("trip_folio"), empresa_id, context)
        return {"ok": True, "data": {"payment": rows[0], "warnings": warnings}}

    def _cancel(self, db: SupabaseClient, context: dict, empresa_id: str) -> dict:
        payment_folio = str(context.get("payment_folio") or "").strip()
        if not payment_folio:
            return {"ok": False, "error": "payment_folio_requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se cancelo", "data": {"payment": {"payment_folio": payment_folio, "status": "cancelled"}}}

        res = db.rest_update("payments", values={"status": "cancelled"}, filters={"empresa_id": f"eq.{empresa_id}", "payment_folio": f"eq.{payment_folio}"})
        if not res.get("ok"):
            return {"ok": False, "error": "db_update_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "payment_not_found"}

        warnings = self._resync(rows[0].get("trip_folio"), empresa_id, context)
        return {"ok": True, "data": {"payment": rows[0], "warnings": warnings}}

    def _resync(self, trip_folio: str | None, empresa_id: str, context: dict) -> list[str]:
        if not trip_folio:
            return ["sin_trip_folio_no_se_resincronizo"]
        sync = _runner().run(
            "vertical_fleet4all_collections/receivables_sync",
            {**context, "empresa_id": empresa_id, "trip_folio": trip_folio, "dry_run": False},
        )
        if not sync.get("ok"):
            return [f"receivables_sync_failed: {sync.get('error')}"]
        return []

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
