from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient


VALID_TYPES = {"customer", "supplier", "both"}


class ErpInventoryPartySaveService:
    def ejecutar(self, context: dict) -> dict:
        party_id = context.get("id")
        schema_context = self._schema_context(context)
        if not schema_context.get("ok", True):
            return schema_context
        party_type = str(context.get("party_type") or "").strip()
        if party_id and not party_type:
            existing = SupabaseClient(schema_context).rest_select("erp_parties", filters={"id": party_id}, select="party_type", limit=1)
            if not existing.get("ok"):
                return existing
            rows = existing.get("data") or []
            party_type = str((rows[0] if rows else {}).get("party_type") or "").strip()
        party_type = party_type or "customer"
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
        if not party_id:
            row.update(
                {
                    "empresa_id": schema_context.get("empresa_id") or schema_context.get("company_id"),
                    "project_code": schema_context.get("project_code"),
                    "module_code": schema_context.get("module_code"),
                }
            )
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se guardo tercero", "data": {"party": row}}

        if party_id:
            row["updated_at"] = context.get("updated_at") or datetime.now(timezone.utc).isoformat()
            result = SupabaseClient(schema_context).rest_update("erp_parties", row, {"id": party_id})
        else:
            if context.get("allow_custom_folio") and context.get("folio"):
                row["folio"] = context.get("folio")
            else:
                folio_result = self._reserve_folio(schema_context, "erp_parties", "PTY")
                if not folio_result.get("ok"):
                    return folio_result
                row["folio"] = folio_result["data"]["folio"]
            result = SupabaseClient(schema_context).rest_insert("erp_parties", row)

        if not result.get("ok"):
            return result
        data = result.get("data") or []
        party = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"party": party}}

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
            **context,
            "schema": schema,
            "company_id": company_id,
            "empresa_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
        }

    def _reserve_folio(self, context: dict, table: str, prefix: str) -> dict:
        service_path = Path(__file__).resolve().parents[2] / "vertical_erp" / "erp_folio_reserve" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_folio_reserve_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_folio_reserve"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpFolioReserveService().ejecutar(
            {
                **context,
                "dry_run": False,
                "table": table,
                "scope": table,
                "prefix": prefix,
                "folio_column": "folio",
                "digits": 5,
            }
        )

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
