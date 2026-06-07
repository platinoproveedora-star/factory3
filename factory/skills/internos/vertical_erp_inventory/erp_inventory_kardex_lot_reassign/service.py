from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient


class ErpInventoryKardexLotReassignService:
    def ejecutar(self, context: dict) -> dict:
        movement_id = str(context.get("id") or context.get("movement_id") or "").strip()
        new_lot_code = self._blank(context.get("lot_code") or context.get("new_lot_code"))
        reason = self._blank(context.get("reason")) or "Reasignacion operativa de lote"
        if not movement_id:
            return {"ok": False, "error": "movement_id requerido"}
        if not new_lot_code:
            return {"ok": False, "error": "lot_code requerido"}

        schema_context = self._schema_context(context)
        if not schema_context.get("ok"):
            return schema_context
        schema_context = schema_context["data"]
        db = SupabaseClient(schema_context)
        existing = db.rest_select("erp_kardex", filters={"id": movement_id}, select="*", limit=1)
        if not existing.get("ok"):
            return existing
        rows = existing.get("data") or []
        if not rows:
            return {"ok": False, "error": "movimiento kardex no encontrado"}
        movement = rows[0]
        previous_lot = self._blank(movement.get("lot_code")) or "GENERAL"
        if previous_lot == new_lot_code:
            return {"ok": True, "data": {"movement": movement, "message": "sin cambios"}}

        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        audit = metadata.get("lot_reassignments") if isinstance(metadata.get("lot_reassignments"), list) else []
        audit.append(
            {
                "previous_lot_code": previous_lot,
                "new_lot_code": new_lot_code,
                "reason": reason,
                "changed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        next_metadata = {
            **metadata,
            "lot_code": new_lot_code,
            "previous_lot_code": previous_lot,
            "lot_reassignments": audit,
        }
        values = {
            "lot_code": new_lot_code,
            "metadata": next_metadata,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se reasigno lote", "data": {"movement": {**movement, **values}}}

        result = db.rest_update("erp_kardex", values, {"id": movement_id})
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        saved = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"movement": saved}}

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or context.get("inventory_schema") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("project_code") or "").strip()
        module_code = str(context.get("module_code") or "").strip()
        missing = [
            key
            for key, value in {
                "schema": schema,
                "company_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
            }.items()
            if not value
        ]
        if missing:
            return {"ok": False, "error": f"contexto ERP incompleto: {', '.join(missing)}"}
        return {
            "ok": True,
            "data": {
                **context,
                "schema": schema,
                "company_id": company_id,
                "empresa_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
            },
        }
