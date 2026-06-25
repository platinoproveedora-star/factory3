from __future__ import annotations
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, money, resolve_billing_context, sales_context  # noqa: E402


class ErpBillingClientProductMonthService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        product_name = blank(context.get("product_name"))
        if not product_name:
            return {"ok": False, "error": "product_name requerido (ej. 'varilla 3/8')"}

        today = date.today()
        date_from = blank(context.get("date_from")) or date(today.year, today.month, 1).isoformat()
        date_to = blank(context.get("date_to")) or today.isoformat()

        sales_ctx_result = sales_context(ctx)
        if not sales_ctx_result.get("ok"):
            return sales_ctx_result
        sales_ctx = sales_ctx_result["data"]
        sales_db = SupabaseClient(sales_ctx)

        # Paso 1: remisiones del rango (no canceladas) → índice {id: customer_name}
        docs_r = sales_db.rest_select(
            "sales_documents",
            filters={"document_type": "eq.remision"},
            select="id,customer_name_snapshot,document_date,status",
            limit=2000,
            order="document_date.desc",
        )
        all_docs = docs_r.get("data") or [] if docs_r.get("ok") else []
        docs_index = {
            d["id"]: (d.get("customer_name_snapshot") or "").strip()
            for d in all_docs
            if date_from <= (d.get("document_date") or "") <= date_to
            and d.get("status") != "cancelada"
            and d.get("id")
        }

        if not docs_index:
            return {"ok": True, "data": {"product_name": product_name, "date_from": date_from, "date_to": date_to, "por_cliente": {}}}

        # Paso 2: items que coincidan con el producto (sin filtrar por doc_id para evitar URLs largas)
        # Se filtra en Python contra docs_index
        items_r = sales_db.rest_select(
            "sales_document_items",
            filters={"product_name_snapshot": f"ilike.%{product_name}%"},
            select="document_id,product_name_snapshot,quantity,line_total",
            limit=5000,
        )
        items = items_r.get("data") or [] if items_r.get("ok") else []

        # Agrupar por cliente, solo items cuyos documentos están en el rango
        por_cliente: dict = defaultdict(float)
        for item in items:
            customer = docs_index.get(item.get("document_id") or "")
            if customer:
                por_cliente[customer] += money(item.get("line_total"))

        return {
            "ok": True,
            "data": {
                "product_name": product_name,
                "date_from": date_from,
                "date_to": date_to,
                "por_cliente": {k: round(v, 2) for k, v in sorted(por_cliente.items(), key=lambda x: x[1], reverse=True)},
            },
        }
