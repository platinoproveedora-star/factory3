from __future__ import annotations


class ErpInventoryProductStoreService:
    def ejecutar(self, context: dict) -> dict:
        name = str(context.get("product_name") or context.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "product_name requerido"}
        identity = self._identity(context)
        if not identity.get("ok"):
            return identity
        row = {
            "folio": context.get("folio"),
            "empresa_id": identity["data"]["empresa_id"],
            "project_code": identity["data"]["project_code"],
            "module_code": identity["data"]["module_code"],
            "product_key": context.get("product_key"),
            "product_name": name,
            "sku": context.get("sku"),
            "category": context.get("category"),
            "unit": context.get("unit") or "pieza",
            "active": context.get("active", True),
            "is_key_product": context.get("is_key_product", False),
            "min_stock": float(context.get("min_stock") or 0),
            "erp_tags": context.get("erp_tags") or {},
            "metadata": context.get("metadata") or {},
        }
        return {"ok": True, "data": {"dry_run": context.get("dry_run", True), "product": row}}

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
