from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"


class SettlementHistoryService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        driver_key = str(context.get("driver_key") or "").strip()

        db = SupabaseClient({**context, "schema": _SCHEMA})

        settlement_filters = {"empresa_id": f"eq.{empresa_id}"}
        if driver_key:
            settlement_filters["driver_key"] = f"eq.{driver_key}"
        settlements_res = db.rest_select("settlements", filters=settlement_filters, select="*")
        if not settlements_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": settlements_res.get("error")}}
        settlements = settlements_res.get("data") or []

        advance_filters = {"empresa_id": f"eq.{empresa_id}", "settled_in": "is.null"}
        if driver_key:
            advance_filters["driver_key"] = f"eq.{driver_key}"
        advances_res = db.rest_select("driver_advances", filters=advance_filters, select="*")
        if not advances_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": advances_res.get("error")}}
        pending_advances = advances_res.get("data") or []

        totals_by_period: dict[tuple, dict] = {}
        for s in settlements:
            key = (s.get("period_from"), s.get("period_to"))
            agg = totals_by_period.setdefault(
                key,
                {"period_from": key[0], "period_to": key[1], "gross_amount": 0.0, "net_amount": 0.0, "count": 0},
            )
            agg["gross_amount"] += float(s.get("gross_amount") or 0)
            agg["net_amount"] += float(s.get("net_amount") or 0)
            agg["count"] += 1

        return {
            "ok": True,
            "data": {
                "settlements": settlements,
                "totals_by_period": list(totals_by_period.values()),
                "pending_advances": pending_advances,
                "warnings": [],
            },
        }
