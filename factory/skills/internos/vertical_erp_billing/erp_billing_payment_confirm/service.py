from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, insert_event, resolve_billing_context, utc_now  # noqa: E402


class ErpBillingPaymentConfirmService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        payment_id = blank(context.get("payment_id") or context.get("payment_folio"))
        if not payment_id:
            return {"ok": False, "error": "payment_id o payment_folio requerido"}

        filters = {"id": payment_id} if len(payment_id) > 20 else {"folio": payment_id}
        payment = fetch_one(SupabaseClient(ctx), "billing_payments", filters, "id,folio,status,confirmation_status,payment_method")
        if not payment:
            return {"ok": False, "error": "pago no encontrado"}
        if payment.get("confirmation_status") == "confirmado":
            return {"ok": False, "error": "el pago ya esta confirmado"}

        bank_reference = blank(context.get("bank_reference") or context.get("reference") or context.get("tracking_key"))

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se confirmo pago", "data": {"payment_id": payment["id"], "folio": payment.get("folio"), "bank_reference": bank_reference}}

        update = {"confirmation_status": "confirmado", "confirmed_at": utc_now(), "updated_at": utc_now()}
        if bank_reference:
            update["bank_reference"] = bank_reference

        result = SupabaseClient(ctx).rest_update("billing_payments", update, {"id": payment["id"]})
        if not result.get("ok"):
            return result

        insert_event(ctx, "payment_confirmed", {"payment_id": payment["id"], "folio": payment.get("folio"), "bank_reference": bank_reference}, False)
        return {"ok": True, "data": {"payment_id": payment["id"], "folio": payment.get("folio"), "confirmation_status": "confirmado"}}
