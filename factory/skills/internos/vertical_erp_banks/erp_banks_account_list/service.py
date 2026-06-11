from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _banks_common import SupabaseClient, resolve_banks_context  # noqa: E402


class ErpBanksAccountListService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_banks_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        filters: dict = {"empresa_id": ctx["company_id"]}
        status = str(context.get("status") or "").strip()
        if status:
            filters["status"] = status

        limit = min(int(context.get("limit") or 200), 500)
        result = SupabaseClient(ctx).rest_select(
            "banks_accounts",
            filters=filters,
            select="id,folio,account_type,account_name,bank_name,account_number_mask,holder_name,currency,responsible_user,status,current_balance,opening_balance,metadata,created_at",
            order="account_name.asc",
            limit=limit,
        )
        if not result.get("ok"):
            return result

        accounts = result.get("data") or []
        total_balance = round(sum(float(a.get("current_balance") or 0) for a in accounts), 2)
        active_count = sum(1 for a in accounts if str(a.get("status") or "") == "active")
        return {
            "ok": True,
            "data": {
                "accounts": accounts,
                "total_balance": total_balance,
                "active_count": active_count,
                "count": len(accounts),
            },
        }
