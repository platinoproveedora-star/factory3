from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, insert_event, money, resolve_billing_context, utc_now  # noqa: E402


class ErpBillingCashCutCloseService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        cut_id = blank(context.get("cash_cut_id") or context.get("id"))
        folio = blank(context.get("cash_cut_folio") or context.get("folio"))
        if not cut_id and not folio:
            return {"ok": False, "error": "cash_cut_id o cash_cut_folio requerido"}
        db = SupabaseClient(ctx)
        cash_cut = fetch_one(db, "billing_cash_cuts", {"id": cut_id} if cut_id else {"folio": folio})
        if not cash_cut:
            return {"ok": False, "error": "corte no encontrado"}
        counted = money(context.get("counted_amount"))
        expected = money(context.get("expected_amount") if context.get("expected_amount") is not None else cash_cut.get("expected_amount"))
        destination_account_id = blank(context.get("money_account_id") or context.get("destination_money_account_id") or cash_cut.get("money_account_id"))
        update = {
            "counted_amount": counted,
            "expected_amount": expected,
            "difference_amount": round(counted - expected, 2),
            "money_account_id": destination_account_id,
            "status": "cerrado",
            "notes": blank(context.get("notes")) or cash_cut.get("notes"),
            "updated_at": utc_now(),
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se cerro corte", "data": {"cash_cut": {**cash_cut, **update}}}
        cut_result = db.rest_update("billing_cash_cuts", update, {"id": cash_cut["id"]})
        if not cut_result.get("ok"):
            return cut_result
        account_update = None
        if destination_account_id and counted:
            account = fetch_one(db, "billing_money_accounts", {"id": destination_account_id}, "id,current_balance")
            if account:
                account_update = db.rest_update(
                    "billing_money_accounts",
                    {"current_balance": money(account.get("current_balance")) + counted, "updated_at": utc_now()},
                    {"id": destination_account_id},
                )
        insert_event(ctx, "cash_cut_closed", {"cash_cut_id": cash_cut["id"], "counted_amount": counted, "difference_amount": update["difference_amount"]}, False)
        data = cut_result.get("data") or []
        saved = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"cash_cut": saved, "account_update": account_update.get("data") if isinstance(account_update, dict) else None}}
