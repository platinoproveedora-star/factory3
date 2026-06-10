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
        doc = self._document(ctx, context)
        expected_amount = money(context.get("expected_amount") if context.get("expected_amount") is not None else (doc or {}).get("balance_total") or (doc or {}).get("total"))
        customer_id = blank(context.get("customer_id") or (doc or {}).get("customer_id"))
        customer_name = blank(context.get("customer_name") or (doc or {}).get("customer_name_snapshot"))
        sales_doc_id = blank(context.get("sales_document_id") or context.get("document_id") or (doc or {}).get("id"))
        sales_folio = blank(context.get("sales_folio") or context.get("document_folio") or (doc or {}).get("folio"))

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
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
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
