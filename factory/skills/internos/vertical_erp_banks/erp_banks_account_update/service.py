from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _banks_common import SupabaseClient, blank, resolve_banks_context, utc_now  # noqa: E402


VALID_TYPES = {"bank", "cash", "cash_box", "collector_cash", "card_terminal", "other"}
VALID_STATUS = {"active", "inactive", "archived"}


class ErpBanksAccountUpdateService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_banks_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        account_id = blank(context.get("account_id") or context.get("id"))
        account_folio = blank(context.get("account_folio") or context.get("folio"))
        if not account_id and not account_folio:
            return {"ok": False, "error": "account_id o account_folio requerido"}

        update: dict = {}
        if "account_type" in context:
            account_type = str(context.get("account_type") or "").strip()
            if account_type not in VALID_TYPES:
                return {"ok": False, "error": f"account_type invalido. Opciones: {', '.join(sorted(VALID_TYPES))}"}
            update["account_type"] = account_type
        if "account_name" in context:
            account_name = str(context.get("account_name") or "").strip()
            if not account_name:
                return {"ok": False, "error": "account_name requerido"}
            update["account_name"] = account_name
        for key in ("bank_name", "holder_name", "responsible_user"):
            if key in context:
                update[key] = blank(context.get(key))
        if "account_number" in context:
            account_number = blank(context.get("account_number"))
            update["account_number"] = account_number
            update["account_number_mask"] = blank(context.get("account_number_mask")) or self._mask(account_number)
        elif "account_number_mask" in context:
            update["account_number_mask"] = blank(context.get("account_number_mask"))
        if "status" in context:
            status = str(context.get("status") or "").strip()
            if status not in VALID_STATUS:
                return {"ok": False, "error": f"status invalido. Opciones: {', '.join(sorted(VALID_STATUS))}"}
            update["status"] = status
        if not update:
            return {"ok": False, "error": "sin campos para actualizar"}
        update["updated_at"] = utc_now()

        filters = {"empresa_id": ctx["company_id"]}
        if account_id:
            filters["id"] = account_id
        else:
            filters["folio"] = account_folio

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo cuenta", "data": {"account": {**filters, **update}}}

        result = SupabaseClient(ctx).rest_update("banks_accounts", update, filters)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        account = data[0] if isinstance(data, list) and data else data
        if not account:
            return {"ok": False, "error": "cuenta no encontrada"}
        return {"ok": True, "data": {"account": account}}

    def _mask(self, number: object) -> str | None:
        s = str(number or "").strip()
        return f"****{s[-4:]}" if len(s) >= 4 else None
