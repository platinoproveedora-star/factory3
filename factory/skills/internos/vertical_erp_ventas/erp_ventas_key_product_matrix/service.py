from __future__ import annotations

from datetime import date, timedelta

from factory.engine import SupabaseClient


class ErpVentasKeyProductMatrixService:
    def ejecutar(self, context: dict) -> dict:
        start_date = str(context.get("start_date") or (date.today() - timedelta(days=7)).isoformat())
        end_date = str(context.get("end_date") or date.today().isoformat())
        product_limit = int(context.get("product_limit") or 6)
        inventory_context = self._inventory_context(context)
        if not inventory_context.get("ok"):
            return inventory_context
        sales_context = self._sales_context(context)
        if not sales_context.get("ok"):
            return sales_context

        products_res = SupabaseClient(inventory_context["data"]).rest_select(
            "erp_products",
            filters={"active": "eq.true", "is_key_product": "eq.true"},
            select="id,folio,product_name,unit",
            order="product_name.asc",
            limit=product_limit,
        )
        if not products_res.get("ok"):
            return products_res
        products = products_res.get("data") or []
        product_ids = [p["id"] for p in products if p.get("id")]

        docs_res = SupabaseClient(sales_context["data"]).rest_select(
            "sales_documents",
            filters={"document_type": "eq.remision", "document_date": f"gte.{start_date}"},
            select="id,folio,external_folio,customer_name_snapshot,document_date,total",
            order="document_date.asc",
            limit=5000,
        )
        if not docs_res.get("ok"):
            return docs_res
        docs = [d for d in (docs_res.get("data") or []) if str(d.get("document_date") or "") <= end_date]
        if not docs or not product_ids:
            return {"ok": True, "data": {"products": products, "rows": [], "totals": {}, "grand_total": 0, "start_date": start_date, "end_date": end_date}}

        doc_ids = [d["id"] for d in docs if d.get("id")]
        items_res = SupabaseClient(sales_context["data"]).rest_select(
            "sales_document_items",
            filters={"document_id": f"in.({','.join(doc_ids)})"},
            select="document_id,inventory_product_id,product_id,quantity,unit_price,tax_amount,line_total",
            limit=10000,
        )
        if not items_res.get("ok"):
            return items_res

        by_doc: dict[str, dict[str, float]] = {}
        for item in items_res.get("data") or []:
            product_id = item.get("inventory_product_id") or item.get("product_id")
            if product_id not in product_ids:
                continue
            doc_map = by_doc.setdefault(item.get("document_id"), {})
            net = float(item.get("quantity") or 0) * float(item.get("unit_price") or 0)
            doc_map[product_id] = doc_map.get(product_id, 0.0) + net

        totals = {product_id: 0.0 for product_id in product_ids}
        rows = []
        for doc in docs:
            values = by_doc.get(doc.get("id"), {})
            row_total = 0.0
            cells = {}
            for product_id in product_ids:
                amount = round(values.get(product_id, 0.0), 2)
                cells[product_id] = amount
                totals[product_id] += amount
                row_total += amount
            if row_total <= 0:
                continue
            rows.append({**doc, "products": cells, "row_total": round(row_total, 2)})
        totals = {key: round(value, 2) for key, value in totals.items()}
        return {
            "ok": True,
            "data": {
                "products": products,
                "rows": rows,
                "totals": totals,
                "grand_total": round(sum(totals.values()), 2),
                "start_date": start_date,
                "end_date": end_date,
            },
        }

    def _sales_context(self, context: dict) -> dict:
        schema = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_ventas/sales_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}

    def _inventory_context(self, context: dict) -> dict:
        schema = str(context.get("schema_inventario") or context.get("inventory_schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_inventario/inventory_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
