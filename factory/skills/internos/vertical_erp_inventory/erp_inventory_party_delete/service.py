from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient


class ErpInventoryPartyDeleteService:
    def ejecutar(self, context: dict) -> dict:
        party_id = str(context.get("id") or context.get("party_id") or "").strip()
        if not party_id:
            return {"ok": False, "error": "id requerido"}

        schema_context = {
            **context,
            "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004",
            "company_id": context.get("company_id") or "EMP_DURALON",
            "project_code": context.get("project_code") or "PROY-004",
            "module_code": context.get("module_code") or "inventario",
        }
        db = SupabaseClient(schema_context)
        existing = db.rest_select("erp_parties", filters={"id": party_id}, select="id,folio,party_type,party_name,active", limit=1)
        if not existing.get("ok"):
            return existing
        rows = existing.get("data") or []
        if not rows:
            return {"ok": False, "error": "tercero no encontrado"}
        party = rows[0]

        expected_type = str(context.get("party_type") or "").strip()
        if expected_type and party.get("party_type") not in {expected_type, "both"}:
            return {"ok": False, "error": "party_type no coincide con el registro"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se dio de baja tercero", "data": {"party": {**party, "active": False}}}

        result = db.rest_update(
            "erp_parties",
            {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()},
            {"id": party_id},
        )
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        saved = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"party": saved}}
