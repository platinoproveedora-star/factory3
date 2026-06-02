from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient


VALID_TYPES = {"customer", "supplier", "both"}


class ErpInventoryPartySaveService:
    def ejecutar(self, context: dict) -> dict:
        party_id = context.get("id")
        party_type = str(context.get("party_type") or "customer").strip()
        party_name = str(context.get("party_name") or context.get("name") or "").strip()
        if not party_name:
            return {"ok": False, "error": "party_name requerido"}
        if party_type not in VALID_TYPES:
            return {"ok": False, "error": "party_type invalido"}

        row = {
            "party_type": party_type,
            "party_name": party_name,
            "legal_name": self._blank(context.get("legal_name")),
            "rfc": self._blank(context.get("rfc")),
            "phone": self._blank(context.get("phone")),
            "email": self._blank(context.get("email")),
            "address": self._blank(context.get("address")),
            "active": context.get("active", True) is not False,
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se guardo tercero", "data": {"party": row}}

        schema_context = self._schema_context(context)
        if party_id:
            row["updated_at"] = context.get("updated_at") or datetime.now(timezone.utc).isoformat()
            result = SupabaseClient(schema_context).rest_update("erp_parties", row, {"id": party_id})
        else:
            row["folio"] = context.get("folio") or self._next_folio(schema_context, "erp_parties", "PTY")
            result = SupabaseClient(schema_context).rest_insert("erp_parties", row)

        if not result.get("ok"):
            return result
        data = result.get("data") or []
        party = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"party": party}}

    def _schema_context(self, context: dict) -> dict:
        return {
            **context,
            "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004",
            "company_id": context.get("company_id") or "EMP_DURALON",
            "project_code": context.get("project_code") or "PROY-004",
            "module_code": context.get("module_code") or "inventario",
        }

    def _next_folio(self, context: dict, table: str, prefix: str) -> str:
        result = SupabaseClient(context).rest_select(table, filters={"folio": f"ilike.{prefix}-%"}, select="folio", limit=100, order="folio.desc")
        numbers = []
        if result.get("ok"):
            for row in result.get("data") or []:
                text = str(row.get("folio") or "")
                if text.startswith(f"{prefix}-") and text.split("-", 1)[1].isdigit():
                    numbers.append(int(text.split("-", 1)[1]))
        return f"{prefix}-{max(numbers or [0]) + 1:05d}"

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
