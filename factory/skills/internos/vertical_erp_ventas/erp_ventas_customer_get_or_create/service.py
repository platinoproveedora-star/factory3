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

        row = {
            **context,
            "schema": "uc101_proy004",
            "company_id": "EMP_DURALON",
            "project_code": "PROY-004",
            "module_code": "inventario",
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
        result = SupabaseClient({**context, "schema": "uc101_proy004"}).rest_select(
            "erp_parties",
            filters={"id": f"eq.{customer_id}", "active": "eq.true"},
            select="id,folio,party_name,phone,email,address",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _find_by_name(self, context: dict, customer_name: str) -> dict | None:
        result = SupabaseClient({**context, "schema": "uc101_proy004"}).rest_select(
            "erp_parties",
            filters={"party_name": f"eq.{customer_name}", "party_type": "in.(customer,both)", "active": "eq.true"},
            select="id,folio,party_name,phone,email,address",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _party_save(self, context: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_inventory" / "erp_inventory_party_save" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_party_save_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_party_save"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryPartySaveService().ejecutar(context)
