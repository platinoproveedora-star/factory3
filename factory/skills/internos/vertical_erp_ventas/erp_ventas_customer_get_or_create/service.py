from __future__ import annotations

import importlib.util
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]


class ErpVentasCustomerGetOrCreateService:
    def ejecutar(self, context: dict) -> dict:
        customer_id = str(context.get("customer_id") or "").strip()
        if customer_id:
            customer = self._get_by_id(context, customer_id)
            if customer:
                return {"ok": True, "data": {"customer": customer, "created": False}}
            return {"ok": False, "error": f"cliente no encontrado en erp_parties: {customer_id}"}

        customer_name = str(context.get("customer_name") or context.get("party_name") or "").strip()
        if not customer_name:
            return {"ok": False, "error": "customer_id o customer_name requerido"}

        existing = self._find_by_name(context, customer_name)
        if existing:
            return {"ok": True, "data": {"customer": existing, "created": False}}

        schema_context = self._schema_context(context)
        if not schema_context.get("ok"):
            return schema_context

        row = {
            **schema_context["data"],
            "dry_run": context.get("dry_run", True),
            "party_type": "customer",
            "party_name": customer_name,
            "address": context.get("address") or context.get("delivery_address"),
            "phone": context.get("phone"),
            "email": context.get("email"),
        }
        result = self._party_save(row)
        if not result.get("ok"):
            return result
        party = result.get("data", {}).get("party")
        return {"ok": True, "data": {"customer": party, "created": not context.get("dry_run", True)}}

    def _get_by_id(self, context: dict, customer_id: str) -> dict | None:
        schema_context = self._schema_context(context)
        if not schema_context.get("ok"):
            return None
        result = SupabaseClient(schema_context["data"]).rest_select(
            "erp_parties",
            filters={"id": f"eq.{customer_id}", "active": "eq.true"},
            select="id,folio,party_name,phone,email,address",
            limit=1,
        )
        if not result.get("ok"):
            return None
        rows = self._rows(result.get("data"))
        return rows[0] if rows else None

    def _find_by_name(self, context: dict, customer_name: str) -> dict | None:
        schema_context = self._schema_context(context)
        if not schema_context.get("ok"):
            return None
        result = SupabaseClient(schema_context["data"]).rest_select(
            "erp_parties",
            filters={"party_name": f"eq.{customer_name}", "party_type": "in.(customer,both)", "active": "eq.true"},
            select="id,folio,party_name,phone,email,address",
            limit=1,
        )
        if not result.get("ok"):
            return None
        rows = self._rows(result.get("data"))
        return rows[0] if rows else None

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("schema_inventario") or context.get("inventory_schema") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("project_code") or context.get("project_inv") or context.get("inventory_project_code") or "").strip()
        module_code = str(context.get("module_code") or context.get("module_inv") or context.get("inventory_module_code") or "").strip()
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
            return {"ok": False, "error": f"contexto ERP de cliente incompleto: {', '.join(missing)}"}
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

    def _rows(self, data) -> list[dict]:
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    def _party_save(self, context: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_inventory" / "erp_inventory_party_save" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_party_save_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_party_save"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryPartySaveService().ejecutar(context)
