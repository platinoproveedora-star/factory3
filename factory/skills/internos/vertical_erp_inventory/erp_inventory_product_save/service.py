from __future__ import annotations

import importlib.util
from pathlib import Path

from factory.engine import SupabaseClient


class ErpInventoryProductSaveService:
    def ejecutar(self, context: dict) -> dict:
        name = str(context.get("product_name") or context.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "product_name requerido"}
        schema_context = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        dry_run = context.get("dry_run", True)
        folio = "PROD-DRYRUN"
        if not dry_run:
            if context.get("allow_custom_folio") and context.get("folio"):
                folio = context.get("folio")
            else:
                folio_result = self._reserve_folio(schema_context, "erp_products", "PROD")
                if not folio_result.get("ok"):
                    return folio_result
                folio = folio_result["data"]["folio"]
        row = {
            "folio": folio,
            "product_key": self._blank(context.get("product_key")),
            "product_name": name,
            "sku": self._blank(context.get("sku")),
            "category": self._blank(context.get("category")),
            "category_2": self._blank(context.get("category_2")),
            "brand": self._blank(context.get("brand") or context.get("marca")),
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
