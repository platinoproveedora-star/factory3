from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, insert_event, money, reserve_folio, resolve_billing_context, sales_context, today_iso  # noqa: E402


class ErpBillingCollectionFolioCreateService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        documents_result = self._documents(ctx, context)
        if not documents_result.get("ok"):
            return documents_result
        documents = documents_result["data"]["documents"]
        first_doc = documents[0] if documents else {}
        expected_amount = money(context.get("expected_amount") if context.get("expected_amount") is not None else sum(money(doc.get("amount_to_collect")) for doc in documents))
        if expected_amount <= 0:
            return {"ok": False, "error": "expected_amount debe ser mayor a 0"}
        customer_id = blank(context.get("customer_id") or first_doc.get("customer_id"))
        customer_name = blank(context.get("customer_name") or first_doc.get("customer_name"))
        sales_doc_id = blank(context.get("sales_document_id") or context.get("document_id") or first_doc.get("sales_document_id"))
        sales_folio = blank(context.get("sales_folio") or context.get("document_folio") or first_doc.get("sales_folio"))
        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        metadata = {**metadata, "documents": documents}

        row = {
            **identity_row(ctx),
            "sales_schema": blank(ctx.get("sales_schema") or context.get("sales_schema") or context.get("schema_ventas")),
            "sales_document_id": sales_doc_id,
            "sales_folio": sales_folio,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "expected_amount": expected_amount,
            "collected_amount": 0,
            "balance_amount": expected_amount,
            "status": str(context.get("status") or "emitido").strip() or "emitido",
            "collector_name": blank(context.get("collector_name") or context.get("cobrador")),
            "due_date": blank(context.get("due_date")),
            "ocr_status": "not_required",
            "metadata": metadata,
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se creo folio de cobranza", "data": {"collection_folio": {"folio": "BCF-DRYRUN", **row}}}

        folio_result = reserve_folio(ctx, "billing_collection_folios", "BCF")
        if not folio_result.get("ok"):
            return folio_result
        row["folio"] = folio_result["data"]["folio"]
        result = SupabaseClient(ctx).rest_insert("billing_collection_folios", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        folio = data[0] if isinstance(data, list) and data else data
        insert_event(ctx, "collection_folio_created", {"collection_folio_id": folio.get("id"), "folio": folio.get("folio"), "sales_folio": sales_folio}, False)
        return {"ok": True, "data": {"collection_folio": folio}}

    def _documents(self, ctx: dict, context: dict) -> dict:
        raw_documents = context.get("documents")
        if isinstance(raw_documents, list) and raw_documents:
            documents = []
            customer_key = None
            for raw_doc in raw_documents:
                if not isinstance(raw_doc, dict):
                    return {"ok": False, "error": "documents debe ser una lista de objetos"}
                enriched = self._normalize_document(ctx, raw_doc)
                if not enriched.get("ok"):
                    return enriched
                doc = enriched["data"]
                doc_customer_key = doc.get("customer_id") or doc.get("customer_name")
                if customer_key and doc_customer_key and customer_key != doc_customer_key:
                    return {"ok": False, "error": "todas las remisiones del folio deben ser del mismo cliente"}
                customer_key = customer_key or doc_customer_key
                documents.append(doc)
            return {"ok": True, "data": {"documents": documents}}

        doc = self._document(ctx, context)
        if not doc:
            expected = money(context.get("expected_amount"))
            if expected <= 0:
                return {"ok": False, "error": "sales_document_id/document_id o documents requerido"}
            return {
                "ok": True,
                "data": {
                    "documents": [
                        {
                            "sales_document_id": blank(context.get("sales_document_id") or context.get("document_id")),
                            "sales_folio": blank(context.get("sales_folio") or context.get("document_folio")),
                            "customer_id": blank(context.get("customer_id")),
                            "customer_name": blank(context.get("customer_name")),
                            "document_total": expected,
                            "balance_total": expected,
                            "amount_to_collect": expected,
                        }
                    ]
                },
            }
        return self._documents(ctx, {**context, "documents": [doc]})

    def _normalize_document(self, ctx: dict, raw_doc: dict) -> dict:
        fetched = self._document(ctx, raw_doc) or {}
        doc = {**raw_doc, **{key: value for key, value in fetched.items() if value is not None}}
        status = str(doc.get("status") or "").strip().lower()
        if status == "cancelada":
            return {"ok": False, "error": "no se puede crear folio de una remision cancelada"}
        balance = money(doc.get("balance_total") if doc.get("balance_total") is not None else doc.get("total"))
        amount = money(doc.get("amount_to_collect") if doc.get("amount_to_collect") is not None else doc.get("expected_amount") if doc.get("expected_amount") is not None else balance)
        if amount <= 0:
            return {"ok": False, "error": "cada remision debe tener importe por cobrar mayor a 0"}
        if balance > 0 and amount > balance:
            return {"ok": False, "error": "el importe por cobrar no puede exceder el saldo pendiente de la remision"}
        return {
            "ok": True,
            "data": {
                "sales_document_id": blank(doc.get("sales_document_id") or doc.get("document_id") or doc.get("id")),
                "sales_folio": blank(doc.get("sales_folio") or doc.get("document_folio") or doc.get("folio")),
                "customer_id": blank(doc.get("customer_id")),
                "customer_name": blank(doc.get("customer_name") or doc.get("customer_name_snapshot")),
                "document_total": money(doc.get("document_total") if doc.get("document_total") is not None else doc.get("total")),
                "balance_total": balance,
                "amount_to_collect": amount,
            },
        }

    def _document(self, ctx: dict, context: dict) -> dict | None:
        doc_id = blank(context.get("sales_document_id") or context.get("document_id"))
        folio = blank(context.get("sales_folio") or context.get("document_folio"))
        if not doc_id and not folio:
            return None
        sales_ctx = sales_context(ctx)
        if not sales_ctx.get("ok"):
            return None
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        return fetch_one(
            SupabaseClient(sales_ctx["data"]),
            "sales_documents",
            filters,
            "id,folio,customer_id,customer_name_snapshot,total,paid_total,balance_total,status,document_date",
        )
