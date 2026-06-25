from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, identity_row, insert_event, money, reserve_folio, resolve_billing_context, today_iso  # noqa: E402


class ErpBillingCashCutOpenService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        cut_date = str(context.get("cut_date") or today_iso())
        existing = SupabaseClient(ctx).rest_select(
            "billing_cash_cuts",
            filters={"cut_date": f"eq.{cut_date}", "status": "eq.abierto"},
            select="*",
            limit=1,
        )
        if not existing.get("ok"):
            return existing
        rows = existing.get("data") or []
        if rows:
            return {"ok": True, "data": {"cash_cut": rows[0], "existing": True}}

        row = {
            **identity_row(ctx),
            "collector_name": blank(context.get("collector_name") or context.get("cobrador")),
            "money_account_id": blank(context.get("money_account_id")),
            "cut_date": cut_date,
            "expected_amount": money(context.get("expected_amount")),
            "counted_amount": 0,
            "difference_amount": 0,
            "status": "abierto",
            "notes": blank(context.get("notes")),
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se abrio corte", "data": {"cash_cut": {"folio": "BCUT-DRYRUN", **row}}}
        folio_result = reserve_folio(ctx, "billing_cash_cuts", "BCUT")
        if not folio_result.get("ok"):
            return folio_result
        row["folio"] = folio_result["data"]["folio"]
        result = SupabaseClient(ctx).rest_insert("billing_cash_cuts", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        cash_cut = data[0] if isinstance(data, list) and data else data
        insert_event(ctx, "cash_cut_opened", {"cash_cut_id": cash_cut.get("id"), "folio": cash_cut.get("folio")}, False)
        return {"ok": True, "data": {"cash_cut": cash_cut}}
