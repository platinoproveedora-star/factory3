from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, resolve_followup_context  # noqa: E402


class ErpClientFollowupListService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_followup_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        filters = {
            "empresa_id": ctx["company_id"],
            "project_code": ctx["project_code"],
            "module_code": ctx["module_code"],
        }
        result = SupabaseClient(ctx).rest_select(
            "erp_client_followups",
            filters=filters,
            select="id,folio,customer_id,customer_key,customer_name,comments,last_call_date,next_followup_date,offer_prices,phone,status,updated_at",
            limit=int(context.get("limit") or 5000),
            order="next_followup_date.asc",
        )
        if not result.get("ok"):
            return result

        rows = result.get("data") or []
        requested = context.get("customer_keys")
        if isinstance(requested, list) and requested:
            allowed = {str(key or "").strip().lower() for key in requested if str(key or "").strip()}
            rows = [row for row in rows if str(row.get("customer_key") or "").strip().lower() in allowed]

        return {
            "ok": True,
            "data": {
                "followups": rows,
                "by_customer_key": {row.get("customer_key"): row for row in rows if row.get("customer_key")},
                "total": len(rows),
            },
        }
