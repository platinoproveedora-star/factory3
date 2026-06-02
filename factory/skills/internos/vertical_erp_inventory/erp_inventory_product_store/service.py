from __future__ import annotations


class ErpInventoryProductStoreService:
    def ejecutar(self, context: dict) -> dict:
        name = str(context.get("product_name") or context.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "product_name requerido"}
        row = {
            "folio": context.get("folio"),
            "empresa_id": context.get("empresa_id") or context.get("company_id") or "EMP_DURALON",
            "project_code": context.get("project_code") or "PROY-004",
            "module_code": context.get("module_code") or "inventario",
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

