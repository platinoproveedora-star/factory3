from __future__ import annotations

import re

from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")
_FOLIO_SAFE = re.compile(r"[^A-Za-z0-9_-]+")


class ErpInventoryPriceImportService:
    """Upsert de productos/precios por SKU (sin duplicar) para un catalogo de inventario.

    Pensado para cargas recurrentes: la misma lista de precios se puede volver a
    correr cada mes y solo actualiza el costo de los SKU que ya existen, e
    inserta los que sean nuevos. Nunca borra productos que dejaron de venir en
    la lista.
    """

    def ejecutar(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("project_code") or "").strip()
        module_code = str(context.get("module_code") or "").strip()
        rows_in = context.get("rows")

        if not _VALID_SCHEMA.match(schema):
            return {"ok": False, "error": "schema requerido y valido (snake_case, ej: mi_schema)"}
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not project_code or not module_code:
            return {"ok": False, "error": "project_code y module_code requeridos"}
        if not isinstance(rows_in, list) or not rows_in:
            return {"ok": False, "error": "rows requerido (lista de productos con sku/product_name/costo)"}

        cleaned = self._clean_rows(rows_in)
        if not cleaned:
            return {"ok": False, "error": "no hay filas validas (sku y product_name/nombre son requeridos)"}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio nada",
                "data": {"rows_validas": len(cleaned), "preview": cleaned[:5]},
            }

        inventory_rows = [
            {
                "folio": self._safe_folio(f"PROD-{row['sku']}", 60),
                "empresa_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
                "product_name": row["product_name"],
                "sku": row["sku"],
                "unit": row["unit"],
                "costo_unitario": row["costo"],
                "active": True,
            }
            for row in cleaned
        ]
        inventory_res = self._upsert(
            {**context, "schema": schema}, "erp_products", inventory_rows, on_conflict="empresa_id,sku"
        )
        if not inventory_res.get("ok"):
            return inventory_res

        sync_schema = str(context.get("sync_schema") or "").strip()
        synced = False
        if sync_schema:
            if not _VALID_SCHEMA.match(sync_schema):
                return {"ok": False, "error": "sync_schema invalido (ej: coti4all)"}
            catalog_rows = [
                {
                    "folio": self._safe_folio(f"CAT-{company_id}-{row['sku']}", 80),
                    "empresa_id": company_id,
                    "project_code": project_code,
                    "module_code": module_code,
                    "sku": row["sku"],
                    "nombre": row["product_name"],
                    "unidad": row["unit"],
                    "activo": True,
                    "costo_referencia": row["costo"],
                }
                for row in cleaned
            ]
            sync_res = self._upsert(
                {**context, "schema": sync_schema}, "catalog_items", catalog_rows, on_conflict="empresa_id,sku"
            )
            if not sync_res.get("ok"):
                return sync_res
            synced = True

        return {
            "ok": True,
            "data": {
                "schema": schema,
                "company_id": company_id,
                "rows_procesadas": len(cleaned),
                "sync_schema": sync_schema or None,
                "synced": synced,
            },
        }

    def _clean_rows(self, rows_in: list) -> list[dict]:
        cleaned: list[dict] = []
        seen: set[str] = set()
        for raw in rows_in:
            if not isinstance(raw, dict):
                continue
            sku = str(raw.get("sku") or raw.get("codigo") or "").strip()
            name = str(raw.get("product_name") or raw.get("nombre") or "").strip()
            if not sku or not name or sku in seen:
                continue
            seen.add(sku)
            costo_raw = raw.get("costo_unitario", raw.get("costo", raw.get("precio", raw.get("precio_unitario", 0))))
            try:
                costo = round(float(costo_raw or 0), 2)
            except (TypeError, ValueError):
                costo = 0.0
            cleaned.append(
                {
                    "sku": sku,
                    "product_name": name,
                    "unit": str(raw.get("unit") or raw.get("unidad") or "pieza").strip() or "pieza",
                    "costo": costo,
                }
            )
        return cleaned

    def _upsert(self, ctx: dict, table: str, rows: list[dict], on_conflict: str) -> dict:
        client = SupabaseClient(ctx)
        check = client.check_config(require_rest=True)
        if not check.get("ok"):
            return check
        batch_size = 200
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            res = client.rest_upsert(table, batch, on_conflict=on_conflict)
            if not res.get("ok"):
                return res
        return {"ok": True}

    def _safe_folio(self, value: str, max_len: int) -> str:
        return _FOLIO_SAFE.sub("-", value).strip("-")[:max_len]
