from __future__ import annotations


VALID_TYPES = {"customer", "supplier", "both"}


class ErpInventoryPartyStoreService:
    def ejecutar(self, context: dict) -> dict:
        name = str(context.get("party_name") or context.get("name") or "").strip()
        party_type = str(context.get("party_type") or "customer").strip()
        if not name:
            return {"ok": False, "error": "party_name requerido"}
        if party_type not in VALID_TYPES:
            return {"ok": False, "error": "party_type invalido: customer | supplier | both"}
        row = {
            "folio": context.get("folio"),
            "empresa_id": context.get("empresa_id") or context.get("company_id") or "EMP_DURALON",
            "project_code": context.get("project_code") or "PROY-004",
            "module_code": context.get("module_code") or "inventario",
            "party_type": party_type,
            "party_name": name,
            "legal_name": context.get("legal_name"),
            "rfc": context.get("rfc"),
            "phone": context.get("phone"),
            "email": context.get("email"),
            "address": context.get("address"),
            "active": context.get("active", True),
            "erp_tags": context.get("erp_tags") or {},
            "metadata": context.get("metadata") or {},
        }
        return {"ok": True, "data": {"dry_run": context.get("dry_run", True), "party": row}}

