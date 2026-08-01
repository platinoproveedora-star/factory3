from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, insert_event, money, resolve_billing_context, sales_context, utc_now  # noqa: E402


_VALID_METHODS = {"cash", "transfer", "deposit", "card", "check", "other"}


class ErpBillingPaymentManageService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        action = str(context.get("action") or "").strip().lower()
        if action not in {"update", "cancel"}:
            return {"ok": False, "error": "action requerido: update|cancel"}

        payment = self._payment(ctx, context)
        if not payment:
            return {"ok": False, "error": "payment_id/payment_folio requerido o no encontrado"}
        if str(payment.get("status") or "").strip().lower() == "cancelado":
            return {"ok": False, "error": "el pago ya esta cancelado"}

        if action == "cancel":
            return self._cancel(ctx, context, payment)
        return self._update(ctx, context, payment)

    def _update(self, ctx: dict, context: dict, payment: dict) -> dict:
        apps = self._active_applications(ctx, payment["id"])
        applied_total = money(sum(money(app.get("amount_applied")) for app in apps))
        update = {}
        if context.get("amount") is not None:
            amount = money(context.get("amount"))
            if amount <= 0:
                return {"ok": False, "error": "amount debe ser mayor a 0"}
            if amount < applied_total:
                return {"ok": False, "error": "amount no puede ser menor al total ya aplicado"}
            update["amount"] = amount
            update["unapplied_amount"] = money(amount - applied_total)
            update["status"] = "aplicado" if update["unapplied_amount"] <= 0 else "parcial" if applied_total > 0 else "sin_aplicar"
        if context.get("payment_method"):
            method = str(context.get("payment_method") or "").strip()
            if method not in _VALID_METHODS:
                return {"ok": False, "error": "payment_method invalido"}
            update["payment_method"] = method
        for key in ["payment_date", "tracking_key", "reference", "bank_reference", "notes"]:
            if key in context:
                update[key] = blank(context.get(key))
        if "destination_money_account_id" in context:
            update["destination_money_account_id"] = blank(context.get("destination_money_account_id"))
        if "destination_bank_account_id" in context:
            metadata = payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}
            update["metadata"] = {
                **metadata,
                "destination_bank_account_id": blank(context.get("destination_bank_account_id")),
            }
        update["updated_at"] = utc_now()

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se modifico pago", "data": {"payment": {**payment, **update}, "applied_total": applied_total}}

        result = SupabaseClient(ctx).rest_update("billing_payments", update, {"id": payment["id"]})
        if not result.get("ok"):
            return result
        insert_event(ctx, "payment_updated", {"payment_id": payment["id"], "folio": payment.get("folio"), "changes": sorted(update.keys())}, False)
        rows = result.get("data") or []
        return {"ok": True, "data": {"payment": rows[0] if isinstance(rows, list) and rows else rows}}

    def _cancel(self, ctx: dict, context: dict, payment: dict) -> dict:
        sales_ctx_result = sales_context(ctx)
        if not sales_ctx_result.get("ok"):
            return sales_ctx_result
        sales_ctx = sales_ctx_result["data"]

        apps = self._active_applications(ctx, payment["id"])
        reversals = []
        for app in apps:
            document = fetch_one(
                SupabaseClient(sales_ctx),
                "sales_documents",
                {"id": app.get("sales_document_id")},
                "id,folio,total,paid_total,balance_total,status,document_type",
            )
            if not document:
                continue
            new_paid = money(document.get("paid_total")) - money(app.get("amount_applied"))
            new_paid = max(new_paid, 0)
            new_balance = max(money(document.get("total")) - new_paid, 0)
            status = "cancelada" if str(document.get("status") or "") == "cancelada" else "pagada" if new_balance <= 0 else "parcial" if new_paid > 0 else "pendiente"
            reversals.append(
                {
                    "application_id": app.get("id"),
                    "sales_document_id": document.get("id"),
                    "sales_folio": document.get("folio"),
                    "amount": money(app.get("amount_applied")),
                    "document_update": {"paid_total": new_paid, "balance_total": new_balance, "status": status},
                }
            )

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se cancelo pago", "data": {"payment_id": payment["id"], "folio": payment.get("folio"), "applications_to_cancel": len(apps), "reversals": reversals}}

        now = utc_now()
        billing_db = SupabaseClient(ctx)
        sales_db = SupabaseClient(sales_ctx)
        for reversal in reversals:
            app = next((row for row in apps if row.get("id") == reversal["application_id"]), {})
            app_metadata = app.get("metadata") if isinstance(app.get("metadata"), dict) else {}
            doc_result = sales_db.rest_update(
                "sales_documents",
                {**reversal["document_update"], "updated_at": now},
                {"id": reversal["sales_document_id"]},
            )
            if not doc_result.get("ok"):
                return doc_result
            app_result = billing_db.rest_update(
                "billing_payment_applications",
                {
                    "status": "cancelado",
                    "updated_at": now,
                    "metadata": {
                        **app_metadata,
                        "cancelled_by_payment_id": payment["id"],
                        "cancelled_payment_folio": payment.get("folio"),
                        "cancel_reason": blank(context.get("reason") or context.get("cancel_reason")) or "Cancelacion de pago",
                    },
                },
                {"id": reversal["application_id"]},
            )
            if not app_result.get("ok"):
                return app_result

        pay_result = billing_db.rest_update(
            "billing_payments",
            {
                "status": "cancelado",
                "unapplied_amount": 0,
                "updated_at": now,
                "metadata": {
                    **(payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}),
                    "cancelled": True,
                    "cancelled_at": now,
                    "cancel_reason": blank(context.get("reason") or context.get("cancel_reason")) or "Cancelacion de pago",
                    "cancelled_applications": [app.get("folio") for app in apps],
                },
            },
            {"id": payment["id"]},
        )
        if not pay_result.get("ok"):
            return pay_result
        insert_event(ctx, "payment_cancelled", {"payment_id": payment["id"], "folio": payment.get("folio"), "applications": len(apps)}, False)
        rows = pay_result.get("data") or []
        return {"ok": True, "data": {"payment": rows[0] if isinstance(rows, list) and rows else rows, "reversals": reversals}}

    def _active_applications(self, ctx: dict, payment_id: str) -> list[dict]:
        result = SupabaseClient(ctx).rest_select(
            "billing_payment_applications",
            filters={"payment_id": payment_id},
            select="id,folio,payment_id,sales_document_id,sales_folio,amount_applied,status,metadata",
            limit=500,
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "error leyendo aplicaciones")
        return [row for row in result.get("data") or [] if str(row.get("status") or "") == "aplicado"]

    def _payment(self, ctx: dict, context: dict) -> dict | None:
        payment_id = blank(context.get("payment_id"))
        folio = blank(context.get("payment_folio") or context.get("folio"))
        if not payment_id and not folio:
            return None
        filters = {"id": payment_id} if payment_id else {"folio": folio}
        return fetch_one(SupabaseClient(ctx), "billing_payments", filters)
