from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient


class ErpVentasRemisionUpdateService:
    ALLOWED_STATUS = {"emitida", "pendiente", "pagada", "cancelada"}

    def ejecutar(self, context: dict) -> dict:
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}

        update = {}
        for field in ("external_folio", "delivery_address", "notes"):
            if field in context:
                update[field] = self._blank(context.get(field))
        if "status" in context:
            status = str(context.get("status") or "").strip()
            if status not in self.ALLOWED_STATUS:
                return {"ok": False, "error": "status invalido"}
            update["status"] = status
        if not update:
            return {"ok": False, "error": "sin campos editables para actualizar"}
        update["updated_at"] = datetime.now(timezone.utc).isoformat()

        ctx = {**context, "schema": context.get("schema_ventas") or "uc101_proy002"}
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo remision", "data": {"remision": {**filters, **update}}}

        result = SupabaseClient(ctx).rest_update("sales_documents", update, filters)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        remision = data[0] if isinstance(data, list) and data else data
        if not remision:
            return {"ok": False, "error": "remision no encontrada"}
        if "delivery_address" in update:
            self._sync_kardex_delivery_address(context, remision.get("folio"), update.get("delivery_address"))
        return {"ok": True, "data": {"remision": remision}}

    def _sync_kardex_delivery_address(self, context: dict, remision_folio: str | None, delivery_address: str | None) -> None:
        if not remision_folio:
            return
        SupabaseClient({**context, "schema": context.get("schema_inventario") or "uc101_proy004"}).rest_update(
            "erp_kardex",
            {"delivery_address": delivery_address},
            {"source_type": "remision", "source_folio": remision_folio},
        )

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
