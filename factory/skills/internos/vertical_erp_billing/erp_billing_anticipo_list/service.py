from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, resolve_billing_context  # noqa: E402


class ErpBillingAnticipoListService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        filters: dict = {}
        if context.get("customer_name"):
            filters["customer_name"] = f"ilike.%{context['customer_name']}%"
        if context.get("customer_id"):
            filters["customer_id"] = f"eq.{context['customer_id']}"
        if context.get("status"):
            filters["status"] = f"eq.{context['status']}"

        limit = int(context.get("limit") or 200)
        result = SupabaseClient(ctx).rest_select(
            "billing_anticipos",
            filters=filters,
            select="*",
            limit=limit,
            order="payment_date.desc,created_at.desc",
        )
        if not result.get("ok"):
            return result

        rows = result.get("data") or []
        disponibles = [r for r in rows if r.get("status") == "disponible"]
        total_disponible = sum(float(r.get("unapplied_amount") or 0) for r in disponibles)

        return {
            "ok": True,
            "data": {
                "anticipos": rows,
                "total": len(rows),
                "total_disponible": round(total_disponible, 2),
            },
        }
