from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, resolve_billing_context  # noqa: E402


class ErpBillingDevolucionListService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        filters: dict = {}
        status = blank(context.get("status"))
        customer_name = blank(context.get("customer_name"))
        customer_id = blank(context.get("customer_id"))
        date_from = blank(context.get("date_from"))
        date_to = blank(context.get("date_to"))

        if status:
            filters["status"] = f"eq.{status}"
        if customer_id:
            filters["customer_id"] = f"eq.{customer_id}"
        elif customer_name:
            filters["customer_name"] = f"ilike.%{customer_name}%"
        if date_from:
            filters["created_at"] = f"gte.{date_from}"
        if date_to:
            filters.setdefault("created_at", f"lte.{date_to}")

        limit = min(int(context.get("limit") or 100), 500)
        db = SupabaseClient(ctx)
        r = db.rest_select("billing_devoluciones", filters=filters, select="*", limit=limit, order="created_at.desc")
        if not r.get("ok"):
            return r

        devoluciones = r.get("data") or []
        return {"ok": True, "data": {"devoluciones": devoluciones, "total": len(devoluciones)}}
