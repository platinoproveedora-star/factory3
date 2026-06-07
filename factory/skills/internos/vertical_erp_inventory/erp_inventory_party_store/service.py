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
        identity = self._identity(context)
        if not identity.get("ok"):
            return identity
        row = {
            "folio": context.get("folio"),
            "empresa_id": identity["data"]["empresa_id"],
            "project_code": identity["data"]["project_code"],
            "module_code": identity["data"]["module_code"],
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

    def _identity(self, context: dict) -> dict:
        data = {
            "empresa_id": str(context.get("empresa_id") or context.get("company_id") or "").strip(),
            "project_code": str(context.get("project_code") or "").strip(),
            "module_code": str(context.get("module_code") or "").strip(),
        }
        missing = [key for key, value in data.items() if not value]
        if missing:
            return {"ok": False, "error": f"identidad ERP incompleta: {', '.join(missing)}"}
        return {"ok": True, "data": data}
