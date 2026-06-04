from __future__ import annotations

from datetime import datetime

from factory.engine import SupabaseClient


class ErpInventoryKardexListService:
    def ejecutar(self, context: dict) -> dict:
        limit = min(int(context.get("limit") or 20), 500)
        start_date = str(context.get("start_date") or "").strip()
        end_date = str(context.get("end_date") or "").strip()
        product_id = str(context.get("product_id") or "").strip()
        source_type = str(context.get("source_type") or "").strip()
        if start_date and end_date:
            start = self._as_date(start_date)
            end = self._as_date(end_date)
            if not start or not end:
                return {"ok": False, "error": "rango de fechas invalido"}
            if (end - start).days > 62:
                return {"ok": False, "error": "el rango maximo permitido es de 2 meses"}

        filters = {}
        if product_id:
            filters["product_id"] = product_id
        if source_type:
            filters["source_type"] = source_type
        if start_date:
            filters["movement_date"] = f"gte.{start_date}"

        ctx = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        db = SupabaseClient(ctx)
        result = db.rest_select(
            "erp_kardex",
            filters=filters,
            select="*",
            order="movement_date.desc,created_at.desc",
            limit=limit,
        )
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        if end_date:
            rows = [row for row in rows if str(row.get("movement_date") or "") <= end_date]
        rows = self._with_products(db, rows)
        return {"ok": True, "data": {"movements": rows, "limit": limit, "start_date": start_date or None, "end_date": end_date or None, "product_id": product_id or None, "source_type": source_type or None}}

    def _as_date(self, value: str):
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            return None

    def _with_products(self, db: SupabaseClient, rows: list[dict]) -> list[dict]:
        if not rows:
            return rows
        products_res = db.rest_select("erp_products", select="id,folio,product_key,product_name,sku,category,unit", limit=10000)
        if not products_res.get("ok"):
            return rows
        products = {str(product.get("id")): product for product in products_res.get("data") or []}
        enriched = []
        for row in rows:
            product = products.get(str(row.get("product_id") or "")) or {}
            enriched.append(
                {
                    **row,
                    "product_folio": row.get("product_folio") or product.get("folio"),
                    "product_key": row.get("product_key") or product.get("product_key"),
                    "product_name": row.get("product_name") or product.get("product_name"),
                    "sku": row.get("sku") or product.get("sku"),
                    "category": row.get("category") or product.get("category"),
                    "unit": row.get("unit") or product.get("unit"),
                }
            )
        return enriched
