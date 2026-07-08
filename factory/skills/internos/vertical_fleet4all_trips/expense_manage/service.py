from __future__ import annotations

from datetime import date, timedelta

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_MAX_LIMIT = 1000


class ExpenseManageService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        action = str(context.get("action") or "list").strip().lower()
        db = SupabaseClient({**context, "schema": context.get("schema") or _SCHEMA})
        if action == "list":
            return self._list(db, context, empresa_id)
        if action == "update":
            return self._update(db, context, empresa_id)
        if action == "delete":
            return self._delete(db, context, empresa_id)
        return {"ok": False, "error": "action_invalida"}

    def _list(self, db: SupabaseClient, context: dict, empresa_id: str) -> dict:
        period = self._period(context)
        filters = {"empresa_id": f"eq.{empresa_id}"}
        if period.get("to"):
            filters["expense_date"] = f"lte.{period['to']}"
        elif period.get("from"):
            filters["expense_date"] = f"gte.{period['from']}"
        if context.get("trip_folio"):
            filters["trip_folio"] = f"eq.{str(context['trip_folio']).strip()}"

        limit = min(max(int(context.get("limit") or 100), 1), _MAX_LIMIT)
        res = db.rest_select(
            "expenses",
            filters=filters,
            select="expense_folio,trip_folio,amount,concept,expense_type,expense_date,driver_key,doc_id,created_at",
            order="expense_date.desc",
            limit=limit,
        )
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        rows = [row for row in (res.get("data") or []) if self._in_period(row.get("expense_date"), period)]
        total = round(sum(float(row.get("amount") or 0) for row in rows), 2)
        return {"ok": True, "data": {"expenses": rows, "period": period, "total": total, "count": len(rows)}}

    def _update(self, db: SupabaseClient, context: dict, empresa_id: str) -> dict:
        expense_folio = str(context.get("expense_folio") or "").strip()
        if not expense_folio:
            return {"ok": False, "error": "expense_folio_requerido"}

        values = {}
        for field in ("trip_folio", "concept", "expense_type", "expense_date", "driver_key"):
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
            return {"ok": True, "message": "dry_run: no se actualizo fleet4all.expenses", "data": {"expense": {"expense_folio": expense_folio, **values}}}

        res = db.rest_update(
            "expenses",
            values=values,
            filters={"empresa_id": f"eq.{empresa_id}", "expense_folio": f"eq.{expense_folio}"},
        )
        if not res.get("ok"):
            return {"ok": False, "error": "db_update_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "expense_not_found"}
        return {"ok": True, "data": {"expense": rows[0], "warnings": []}}

    def _delete(self, db: SupabaseClient, context: dict, empresa_id: str) -> dict:
        expense_folio = str(context.get("expense_folio") or "").strip()
        if not expense_folio:
            return {"ok": False, "error": "expense_folio_requerido"}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se borro fleet4all.expenses", "data": {"expense_folio": expense_folio}}

        res = db.rest_delete(
            "expenses",
            filters={"empresa_id": f"eq.{empresa_id}", "expense_folio": f"eq.{expense_folio}"},
        )
        if not res.get("ok"):
            return {"ok": False, "error": "db_delete_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "expense_not_found"}
        return {"ok": True, "data": {"expense": rows[0], "warnings": []}}

    def _period(self, context: dict) -> dict:
        raw = context.get("period") if isinstance(context.get("period"), dict) else {}
        date_from = raw.get("from") or context.get("from")
        date_to = raw.get("to") or context.get("to")
        if date_from or date_to:
            return {"from": date_from, "to": date_to}
        today = date.today()
        return {"from": (today - timedelta(days=30)).isoformat(), "to": today.isoformat()}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _in_period(self, value: str | None, period: dict) -> bool:
        if not value:
            return True
        if period.get("from") and value < period["from"]:
            return False
        if period.get("to") and value > period["to"]:
            return False
        return True
