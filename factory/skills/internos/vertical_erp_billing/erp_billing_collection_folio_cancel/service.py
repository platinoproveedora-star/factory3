from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, insert_event, resolve_billing_context, utc_now  # noqa: E402


class ErpBillingCollectionFolioCancelService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        folio = self._collection_folio(ctx, context)
        if not folio:
            return {"ok": False, "error": "folio de cobranza no encontrado"}
        if str(folio.get("status") or "").strip() == "cancelado":
            return {"ok": True, "data": {"collection_folio": folio, "already_cancelled": True}}
        payment = self._linked_payment(ctx, folio)
        if folio.get("payment_id") or payment:
            return {"ok": False, "error": "no se puede cancelar un folio con pagos ligados"}

        reason = blank(context.get("cancel_reason") or context.get("reason"))
        metadata = folio.get("metadata") if isinstance(folio.get("metadata"), dict) else {}
        update = {
            "status": "cancelado",
            "updated_at": utc_now(),
            "metadata": {
                **metadata,
                "cancelled": True,
                "cancel_reason": reason,
                "cancelled_at": utc_now(),
            },
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se cancelo folio", "data": {"collection_folio": {**folio, **update}}}

        result = SupabaseClient(ctx).rest_update("billing_collection_folios", update, {"id": folio["id"]})
        if not result.get("ok"):
            return result
        insert_event(ctx, "collection_folio_cancelled", {"collection_folio_id": folio.get("id"), "folio": folio.get("folio"), "reason": reason}, False)
        data = result.get("data") or []
        updated = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"collection_folio": updated}}

    def _collection_folio(self, ctx: dict, context: dict) -> dict | None:
        folio_id = blank(context.get("id") or context.get("collection_folio_id"))
        folio = blank(context.get("folio") or context.get("collection_folio"))
        if not folio_id and not folio:
            return None
        filters = {"id": folio_id} if folio_id else {"folio": folio}
        return fetch_one(SupabaseClient(ctx), "billing_collection_folios", filters)

    def _linked_payment(self, ctx: dict, folio: dict) -> dict | None:
        return fetch_one(SupabaseClient(ctx), "billing_payments", {"collection_folio_id": folio.get("id")}, "id,folio,status")
