from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, insert_event, is_cancelled_sales_document, money, resolve_billing_context, sales_context, utc_now  # noqa: E402


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
        app_plan_result = self._application_update_plan(ctx, context, payment, apps)
        if not app_plan_result.get("ok"):
            return app_plan_result
        app_plan = app_plan_result["data"]
        applied_total = app_plan["planned_applied_total"]
        update = {}
        amount = money(payment.get("amount"))
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
            return {
                "ok": True,
                "message": "dry_run: no se modifico pago",
                "data": {
                    "payment": {**payment, **update},
                    "applied_total": applied_total,
                    "application_updates": app_plan["updates"],
                },
            }

        sales_ctx = app_plan.get("sales_ctx")
        if sales_ctx:
            app_result = self._apply_application_updates(ctx, sales_ctx, payment, app_plan["updates"])
            if not app_result.get("ok"):
                return app_result

        result = SupabaseClient(ctx).rest_update("billing_payments", update, {"id": payment["id"]})
        if not result.get("ok"):
            return result
        insert_event(
            ctx,
            "payment_updated",
            {
                "payment_id": payment["id"],
                "folio": payment.get("folio"),
                "changes": sorted(update.keys()),
                "application_updates": len(app_plan["updates"]),
            },
            False,
        )
        rows = result.get("data") or []
        return {"ok": True, "data": {"payment": rows[0] if isinstance(rows, list) and rows else rows}}

    def _application_update_plan(self, ctx: dict, context: dict, payment: dict, apps: list[dict]) -> dict:
        raw_updates = context.get("applications") or []
        if not raw_updates:
            return {
                "ok": True,
                "data": {
                    "planned_applied_total": money(sum(money(app.get("amount_applied")) for app in apps)),
                    "updates": [],
                    "sales_ctx": None,
                },
            }
        if not isinstance(raw_updates, list):
            return {"ok": False, "error": "applications debe ser lista"}
        sales_ctx_result = sales_context(ctx)
        if not sales_ctx_result.get("ok"):
            return sales_ctx_result
        sales_ctx = sales_ctx_result["data"]
        sales_db = SupabaseClient(sales_ctx)
        apps_by_id = {str(app.get("id")): app for app in apps}
        planned_by_app = {str(app.get("id")): money(app.get("amount_applied")) for app in apps}
        planned_updates = []
        for row in raw_updates:
            if not isinstance(row, dict):
                return {"ok": False, "error": "cada aplicacion debe ser objeto"}
            app_id = blank(row.get("application_id") or row.get("id"))
            if not app_id or app_id not in apps_by_id:
                return {"ok": False, "error": "application_id no encontrado o no activo"}
            app = apps_by_id[app_id]
            new_amount = money(row.get("amount_applied"))
            if new_amount <= 0:
                return {"ok": False, "error": "amount_applied debe ser mayor a 0"}
            new_doc_id = blank(row.get("sales_document_id")) or blank(app.get("sales_document_id"))
            document = self._sales_document(sales_db, new_doc_id)
            if not document:
                return {"ok": False, "error": "remision destino no encontrada"}
            if str(document.get("document_type") or "").strip().lower() != "remision":
                return {"ok": False, "error": "solo se pueden aplicar pagos a remisiones"}
            if is_cancelled_sales_document(document):
                return {"ok": False, "error": "no se puede aplicar a remision cancelada"}
            same_customer = self._same_customer(payment, document)
            if not same_customer.get("ok"):
                return same_customer
            old_doc_id = blank(app.get("sales_document_id"))
            current_balance = money(document.get("balance_total") if document.get("balance_total") is not None else document.get("total"))
            if old_doc_id == new_doc_id:
                current_balance = money(current_balance + money(app.get("amount_applied")))
            if new_amount > current_balance:
                return {"ok": False, "error": f"amount_applied excede saldo de {document.get('folio')}"}
            planned_by_app[app_id] = new_amount
            planned_updates.append({"app": app, "document": document, "new_amount": new_amount})
        planned_total = money(sum(planned_by_app.values()))
        payment_amount = money(context.get("amount") if context.get("amount") is not None else payment.get("amount"))
        if planned_total > payment_amount:
            return {"ok": False, "error": "el total aplicado excede el importe del pago"}
        return {
            "ok": True,
            "data": {
                "planned_applied_total": planned_total,
                "updates": planned_updates,
                "sales_ctx": sales_ctx,
            },
        }

    def _apply_application_updates(self, ctx: dict, sales_ctx: dict, payment: dict, updates: list[dict]) -> dict:
        billing_db = SupabaseClient(ctx)
        sales_db = SupabaseClient(sales_ctx)
        now = utc_now()
        for item in updates:
            app = item["app"]
            old_doc = self._sales_document(sales_db, blank(app.get("sales_document_id")))
            new_doc = item["document"]
            old_amount = money(app.get("amount_applied"))
            new_amount = money(item["new_amount"])
            if old_doc and old_doc.get("id") != new_doc.get("id"):
                old_update = self._document_amount_update(old_doc, -old_amount)
                result = sales_db.rest_update("sales_documents", {**old_update, "updated_at": now}, {"id": old_doc["id"]})
                if not result.get("ok"):
                    return result
                new_update = self._document_amount_update(new_doc, new_amount)
            else:
                new_update = self._document_amount_update(new_doc, new_amount - old_amount)
            doc_result = sales_db.rest_update("sales_documents", {**new_update, "updated_at": now}, {"id": new_doc["id"]})
            if not doc_result.get("ok"):
                return doc_result
            app_metadata = app.get("metadata") if isinstance(app.get("metadata"), dict) else {}
            app_result = billing_db.rest_update(
                "billing_payment_applications",
                {
                    "sales_document_id": new_doc.get("id"),
                    "sales_folio": new_doc.get("folio"),
                    "amount_applied": new_amount,
                    "updated_at": now,
                    "metadata": {**app_metadata, "updated_by_payment_manage": True},
                },
                {"id": app.get("id")},
            )
            if not app_result.get("ok"):
                return app_result
        return {"ok": True}

    def _document_amount_update(self, document: dict, delta: float) -> dict:
        new_paid = max(money(document.get("paid_total")) + money(delta), 0)
        total = money(document.get("total"))
        new_balance = max(total - new_paid, 0)
        status = "pagada" if new_balance <= 0 else "parcial" if new_paid > 0 else "pendiente"
        return {"paid_total": new_paid, "balance_total": new_balance, "status": status}

    def _sales_document(self, sales_db: SupabaseClient, document_id: str | None) -> dict | None:
        if not document_id:
            return None
        return fetch_one(
            sales_db,
            "sales_documents",
            {"id": document_id},
            "id,folio,document_type,customer_id,customer_name_snapshot,total,paid_total,balance_total,status,notes",
        )

    def _same_customer(self, payment: dict, document: dict) -> dict:
        payment_customer_id = blank(payment.get("customer_id"))
        document_customer_id = blank(document.get("customer_id"))
        if payment_customer_id and document_customer_id:
            if payment_customer_id != document_customer_id:
                return {"ok": False, "error": "el pago solo se puede aplicar a remisiones del mismo cliente"}
            return {"ok": True}
        payment_customer = blank(payment.get("customer_name"))
        document_customer = blank(document.get("customer_name_snapshot"))
        if payment_customer and document_customer and payment_customer.strip().lower() != document_customer.strip().lower():
            return {"ok": False, "error": "el pago solo se puede aplicar a remisiones del mismo cliente"}
        return {"ok": True}

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
                "id,folio,total,paid_total,balance_total,status,notes,document_type",
            )
            if not document:
                continue
            new_paid = money(document.get("paid_total")) - money(app.get("amount_applied"))
            new_paid = max(new_paid, 0)
            new_balance = max(money(document.get("total")) - new_paid, 0)
            status = "cancelada" if is_cancelled_sales_document(document) else "pagada" if new_balance <= 0 else "parcial" if new_paid > 0 else "pendiente"
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
