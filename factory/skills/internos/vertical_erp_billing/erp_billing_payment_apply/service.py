from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, insert_event, is_cancelled_sales_document, money, reserve_folio, resolve_billing_context, sales_context, utc_now  # noqa: E402


class ErpBillingPaymentApplyService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        sales_ctx_result = sales_context(ctx)
        if not sales_ctx_result.get("ok"):
            return sales_ctx_result
        sales_ctx = sales_ctx_result["data"]

        payment = self._payment(ctx, context)
        if not payment:
            return {"ok": False, "error": "payment_id/payment_folio requerido o no encontrado"}
        if str(payment.get("status") or "").strip().lower() == "cancelado":
            return {"ok": False, "error": "no se puede aplicar un pago cancelado"}
        document = self._document(sales_ctx, context)
        if not document:
            return {"ok": False, "error": "sales_document_id/sales_folio requerido o no encontrado"}
        if str(document.get("document_type") or "").strip().lower() != "remision":
            return {"ok": False, "error": "solo se pueden aplicar pagos a remisiones; los pedidos no son CXC"}
        if is_cancelled_sales_document(document):
            return {"ok": False, "error": f"no se puede aplicar pago a remision cancelada: {document.get('folio')}"}
        customer_check = self._same_customer(payment, document)
        if not customer_check.get("ok"):
            return customer_check

        unapplied = money(payment.get("unapplied_amount") if payment.get("unapplied_amount") is not None else payment.get("amount"))
        current_balance = money(document.get("balance_total") if document.get("balance_total") is not None else document.get("total"))
        amount = money(context.get("amount_applied") if context.get("amount_applied") is not None else min(unapplied, current_balance))
        if amount <= 0:
            return {"ok": False, "error": "amount_applied debe ser mayor a 0"}
        if amount > unapplied:
            return {"ok": False, "error": "amount_applied excede el saldo no aplicado del pago"}

        new_paid = money(document.get("paid_total")) + amount
        new_balance = max(money(document.get("total")) - new_paid, 0)
        doc_status = "pagada" if new_balance <= 0 else "parcial"
        linked_pedido = self._linked_pedido(sales_ctx, document)
        linked_pedido_update = self._linked_pedido_update(linked_pedido, document, new_paid, new_balance, doc_status)
        payment_unapplied = max(unapplied - amount, 0)
        payment_status = "aplicado" if payment_unapplied <= 0 else "parcial"
        base_metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        application = {
            **identity_row(ctx),
            "payment_id": payment["id"],
            "payment_folio": payment.get("folio"),
            "sales_schema": sales_ctx["schema"],
            "sales_document_id": document["id"],
            "sales_folio": document.get("folio"),
            "amount_applied": amount,
            "status": "aplicado",
            "metadata": {
                **base_metadata,
                "document_total": money(document.get("total")),
                "document_paid_after": new_paid,
                "document_balance_after": new_balance,
                "document_status_after": doc_status,
            },
        }
        preview = {
            "application": {"folio": "BAPP-DRYRUN", **application},
            "document_update": {"paid_total": new_paid, "balance_total": new_balance, "status": doc_status},
            "linked_pedido_update": linked_pedido_update,
            "payment_update": {"unapplied_amount": payment_unapplied, "status": payment_status},
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se aplico pago", "data": preview}

        billing_db = SupabaseClient(ctx)
        sales_db = SupabaseClient(sales_ctx)
        folio_result = reserve_folio(ctx, "billing_payment_applications", "BAPP")
        if not folio_result.get("ok"):
            return folio_result
        application["folio"] = folio_result["data"]["folio"]
        app_result = billing_db.rest_insert("billing_payment_applications", application)
        if not app_result.get("ok"):
            return app_result
        doc_result = sales_db.rest_update(
            "sales_documents",
            {"paid_total": new_paid, "balance_total": new_balance, "status": doc_status, "updated_at": utc_now()},
            {"id": document["id"]},
        )
        if not doc_result.get("ok"):
            return doc_result
        pedido_result = None
        if linked_pedido and linked_pedido_update:
            pedido_result = sales_db.rest_update("sales_documents", linked_pedido_update, {"id": linked_pedido["id"]})
            if not pedido_result.get("ok"):
                return pedido_result
        pay_result = billing_db.rest_update(
            "billing_payments",
            {"unapplied_amount": payment_unapplied, "status": payment_status, "updated_at": utc_now()},
            {"id": payment["id"]},
        )
        if not pay_result.get("ok"):
            return pay_result
        self._update_collection_folios(billing_db, payment, amount)
        insert_event(ctx, "payment_applied", {"payment_id": payment["id"], "document_id": document["id"], "amount": amount}, False)
        app_data = app_result.get("data") or []
        application_saved = app_data[0] if isinstance(app_data, list) and app_data else app_data
        return {
            "ok": True,
            "data": {
                "application": application_saved,
                "document_update": doc_result.get("data"),
                "linked_pedido_update": pedido_result.get("data") if pedido_result else None,
                "payment_update": pay_result.get("data"),
            },
        }

    def _payment(self, ctx: dict, context: dict) -> dict | None:
        payment_id = blank(context.get("payment_id"))
        folio = blank(context.get("payment_folio") or context.get("folio"))
        if not payment_id and not folio:
            return None
        filters = {"id": payment_id} if payment_id else {"folio": folio}
        return fetch_one(SupabaseClient(ctx), "billing_payments", filters)

    def _update_collection_folios(self, billing_db: SupabaseClient, payment: dict, amount: float) -> None:
        ids = []
        metadata = payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}
        raw_folios = metadata.get("collection_folios") if isinstance(metadata.get("collection_folios"), list) else []
        for row in raw_folios:
            if isinstance(row, dict) and blank(row.get("id")):
                ids.append(blank(row.get("id")))
        if not ids and payment.get("collection_folio_id"):
            ids.append(payment["collection_folio_id"])

        remaining = money(amount)
        for collection_id in ids:
            if remaining <= 0:
                break
            collection = fetch_one(billing_db, "billing_collection_folios", {"id": collection_id}, "id,collected_amount,balance_amount")
            if not collection:
                continue
            current_balance = money(collection.get("balance_amount"))
            if current_balance <= 0:
                continue
            applied_to_folio = min(remaining, current_balance)
            collection_collected = money(collection.get("collected_amount")) + applied_to_folio
            collection_balance = max(current_balance - applied_to_folio, 0)
            collection_status = "pagada" if collection_balance <= 0 else "parcial"
            billing_db.rest_update(
                "billing_collection_folios",
                {
                    "collected_amount": collection_collected,
                    "balance_amount": collection_balance,
                    "status": collection_status,
                    "payment_id": payment["id"],
                    "updated_at": utc_now(),
                },
                {"id": collection_id},
            )
            remaining = money(remaining - applied_to_folio)

    def _document(self, sales_ctx: dict, context: dict) -> dict | None:
        doc_id = blank(context.get("sales_document_id") or context.get("document_id"))
        folio = blank(context.get("sales_folio") or context.get("document_folio"))
        if not doc_id and not folio:
            return None
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        return fetch_one(
            SupabaseClient(sales_ctx),
            "sales_documents",
            filters,
            "id,folio,document_type,parent_document_id,root_document_id,customer_id,customer_name_snapshot,total,paid_total,balance_total,status,notes,metadata",
        )

    def _linked_pedido(self, sales_ctx: dict, remision: dict) -> dict | None:
        metadata = remision.get("metadata") if isinstance(remision.get("metadata"), dict) else {}
        pedido_id = blank(remision.get("parent_document_id") or metadata.get("source_pedido_id") or metadata.get("pedido_id"))
        pedido_folio = blank(metadata.get("source_pedido_folio") or metadata.get("pedido_folio"))
        if not pedido_id and not pedido_folio:
            return None
        filters = {"id": pedido_id} if pedido_id else {"folio": pedido_folio}
        return fetch_one(
            SupabaseClient(sales_ctx),
            "sales_documents",
            {**filters, "document_type": "eq.pedido"},
            "id,folio,status,total,paid_total,balance_total,metadata",
        )

    def _linked_pedido_update(self, pedido: dict | None, remision: dict, new_paid: float, new_balance: float, doc_status: str) -> dict | None:
        if not pedido:
            return None
        metadata = pedido.get("metadata") if isinstance(pedido.get("metadata"), dict) else {}
        billing_sync = metadata.get("billing_sync") if isinstance(metadata.get("billing_sync"), dict) else {}
        metadata = {
            **metadata,
            "billing_sync": {
                **billing_sync,
                "source_remision_id": remision.get("id"),
                "source_remision_folio": remision.get("folio"),
                "payment_status": doc_status,
                "paid_total": new_paid,
                "balance_total": new_balance,
                "updated_by_skill": "vertical_erp_billing/erp_billing_payment_apply",
                "updated_at": utc_now(),
            },
        }
        return {
            "paid_total": new_paid,
            "balance_total": new_balance,
            "metadata": metadata,
            "updated_at": utc_now(),
        }

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
