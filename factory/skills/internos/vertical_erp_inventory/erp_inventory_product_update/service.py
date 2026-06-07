from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient


class ErpInventoryProductUpdateService:
    def ejecutar(self, context: dict) -> dict:
        product_id = str(context.get("id") or context.get("product_id") or "").strip()
        if not product_id:
            return {"ok": False, "error": "id requerido"}
        name = str(context.get("product_name") or context.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "product_name requerido"}

        row = {
            "product_key": self._blank(context.get("product_key")),
            "product_name": name,
            "sku": self._blank(context.get("sku")),
            "category": self._blank(context.get("category")),
            "category_2": self._blank(context.get("category_2")),
            "brand": self._blank(context.get("brand") or context.get("marca")),
            "unit": str(context.get("unit") or "pieza").strip() or "pieza",
            "active": context.get("active", True) is not False,
            "is_key_product": bool(context.get("is_key_product", False)),
            "min_stock": float(context.get("min_stock") or 0),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo producto", "data": {"product": {"id": product_id, **row}}}
        schema_context = self._schema_context(context)
        if not schema_context.get("ok"):
            return schema_context
        result = SupabaseClient(schema_context["data"]).rest_update("erp_products", row, {"id": product_id})
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        product = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"product": product}}

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or context.get("inventory_schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema/supabase_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
