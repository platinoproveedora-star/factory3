from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, resolve_billing_context  # noqa: E402


class ErpBillingMoneyAccountListService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        filters = {"empresa_id": ctx["company_id"]}
        if context.get("account_type"):
            filters["account_type"] = str(context["account_type"])
        if context.get("status"):
            filters["status"] = str(context["status"])
        if context.get("responsible_user"):
            filters["responsible_user"] = str(context["responsible_user"])
        limit = min(int(context.get("limit") or 100), 500)
        result = SupabaseClient(ctx).rest_select(
            "billing_money_accounts",
            filters=filters,
            select="id,folio,account_type,account_name,bank_name,account_number_mask,holder_name,currency,responsible_user,status,opening_balance,current_balance,metadata,created_at,updated_at",
            order="account_name.asc",
            limit=limit,
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"accounts": result.get("data") or [], "limit": limit}}
