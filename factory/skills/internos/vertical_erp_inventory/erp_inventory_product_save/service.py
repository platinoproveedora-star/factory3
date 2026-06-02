from __future__ import annotations

from factory.engine import SupabaseClient


class ErpInventoryProductSaveService:
    def ejecutar(self, context: dict) -> dict:
        name = str(context.get("product_name") or context.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "product_name requerido"}
        schema_context = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        dry_run = context.get("dry_run", True)
        row = {
            "folio": context.get("folio") or ("PROD-DRYRUN" if dry_run else self._next_folio(schema_context, "erp_products", "PROD")),
            "product_key": self._blank(context.get("product_key")),
            "product_name": name,
            "sku": self._blank(context.get("sku")),
            "category": self._blank(context.get("category")),
            "unit": context.get("unit") or "pieza",
            "active": context.get("active", True) is not False,
            "is_key_product": bool(context.get("is_key_product", False)),
            "min_stock": float(context.get("min_stock") or 0),
        }
        if dry_run:
            return {"ok": True, "message": "dry_run: no se guardo producto", "data": {"product": row}}
        result = SupabaseClient(schema_context).rest_insert("erp_products", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        product = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"product": product}}

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
