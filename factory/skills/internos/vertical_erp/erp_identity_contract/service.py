from __future__ import annotations


REQUIRED_COLUMNS = [
    "id",
    "folio",
    "empresa_id",
    "project_code",
    "module_code",
    "created_at",
]

OPTIONAL_LINK_COLUMNS = [
    "global_user_id",
    "customer_id",
    "supplier_id",
    "sales_order_id",
    "purchase_order_id",
    "cost_center_id",
    "asset_id",
    "erp_tags",
    "metadata",
]

MODULE_DEFAULT_PREFIXES = {
    "gastos": "GAS",
    "ventas": "VEN",
    "inventario": "INV",
    "compras": "COM",
    "crm": "CLI",
    "cxc": "CXC",
    "cxp": "CXP",
    "erp_core": "ERP",
}


class ErpIdentityContractService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = self._empresa_id(context)
        project_code = str(context.get("project_code") or "").strip()
        module_code = str(context.get("module_code") or context.get("module") or "").strip()
        schema = str(context.get("schema") or context.get("supabase_schema") or "").strip()
        legacy_client_id = str(context.get("legacy_client_id") or context.get("client_id") or "").strip()

        issues = []
        if not empresa_id:
            issues.append("empresa_id/company_id requerido")
        if not project_code:
            issues.append("project_code requerido")
        if not module_code:
            issues.append("module_code requerido")

        folio_prefix = str(context.get("folio_prefix") or MODULE_DEFAULT_PREFIXES.get(module_code, "ERP")).strip()
        required_columns = list(context.get("required_columns") or REQUIRED_COLUMNS)
        optional_link_columns = list(context.get("optional_link_columns") or OPTIONAL_LINK_COLUMNS)

        contract = {
            "empresa_id": empresa_id,
            "company_id": empresa_id,
            "legacy_client_id": legacy_client_id or None,
            "project_code": project_code,
            "module_code": module_code,
            "schema": schema or None,
            "folio_prefix": folio_prefix,
            "required_columns": required_columns,
            "optional_link_columns": optional_link_columns,
            "table_contract": {
                "double_id": ["id", "folio"],
                "identity_columns": ["empresa_id", "project_code", "module_code"],
                "timestamps": ["created_at", "updated_at"],
            },
        }

        return {
            "ok": not issues,
            "data": {
                "contract": contract,
                "issues": issues,
                "ready": not issues,
            },
        }

    def _empresa_id(self, context: dict) -> str:
        return str(
            context.get("empresa_id")
            or context.get("company_id")
            or context.get("empresa")
            or ""
        ).strip()

