from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, identity_row, money, reserve_folio, resolve_banks_context  # noqa: E402

VALID_TYPES = {"bank", "cash", "cash_box", "collector_cash", "card_terminal", "other"}


class ErpBanksAccountCreateService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_banks_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        account_type = str(context.get("account_type") or "").strip()
        account_name = str(context.get("account_name") or "").strip()
        if account_type not in VALID_TYPES:
            return {"ok": False, "error": f"account_type invalido. Opciones: {', '.join(sorted(VALID_TYPES))}"}
        if not account_name:
            return {"ok": False, "error": "account_name requerido"}

        opening_balance = money(context.get("opening_balance") or 0)
        row = {
            **identity_row(ctx),
            "account_type": account_type,
            "account_name": account_name,
            "bank_name": blank(context.get("bank_name")),
            "account_number": blank(context.get("account_number")),
            "account_number_mask": blank(context.get("account_number_mask")) or self._mask(context.get("account_number")),
            "holder_name": blank(context.get("holder_name")),
            "currency": str(context.get("currency") or "MXN").strip().upper(),
            "responsible_user": blank(context.get("responsible_user")),
            "status": "active",
            "current_balance": opening_balance,
            "opening_balance": opening_balance,
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se creo cuenta", "data": {"account": {"folio": "BAC-DRYRUN", **row}}}

        folio_result = reserve_folio(ctx, "banks_accounts", "BAC")
        if not folio_result.get("ok"):
            return folio_result
        row["folio"] = folio_result["data"]["folio"]

        result = SupabaseClient(ctx).rest_insert("banks_accounts", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        account = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"account": account}}

    def _mask(self, number: object) -> str | None:
        s = str(number or "").strip()
        return f"****{s[-4:]}" if len(s) >= 4 else None
