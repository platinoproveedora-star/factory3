from __future__ import annotations

import re

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_FIELDS = [
    "source_system", "source_schema", "source_table", "source_id", "source_folio",
    "source_product_name", "fiscal_product_name", "fiscal_description",
    "sat_product_key", "sat_unit_key", "sat_unit_name", "tax_object",
    "iva_rate", "ieps_rate", "category", "sat_group_key", "status",
]
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class ProductManageService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        action = str(context.get("action") or "list").strip().lower()
        db = SupabaseClient({**context, "schema": _SCHEMA})

        if action == "list":
            return self._list(db, company_id)

        source_product_key = str(context.get("source_product_key") or "").strip()
        fiscal_product_name = str(context.get("fiscal_product_name") or context.get("source_product_name") or "").strip()
        if not source_product_key:
            if not fiscal_product_name:
                return {"ok": False, "error": "source_product_key_o_fiscal_product_name_requerido"}
            source_product_key = "manual:" + _SLUG_RE.sub("-", fiscal_product_name.lower()).strip("-")

        values = {key: context[key] for key in _FIELDS if key in context}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en products", "data": {"company_id": company_id, "source_product_key": source_product_key, **values}}

        existing = db.rest_select("products", filters={"company_id": f"eq.{company_id}", "source_product_key": f"eq.{source_product_key}"}, select="id", limit=1)
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}

        if existing.get("data"):
            res = db.rest_update("products", values, {"company_id": f"eq.{company_id}", "source_product_key": f"eq.{source_product_key}"})
        else:
            row = {
                "folio": f"PRD-{company_id}-{source_product_key}",
                "company_id": company_id,
                "source_product_key": source_product_key,
                "fiscal_product_name": fiscal_product_name or values.get("fiscal_product_name") or source_product_key,
                "status": values.get("status") or "revisar",
                "iva_rate": values.get("iva_rate", 0.16),
                **{key: value for key, value in values.items() if key not in {"fiscal_product_name", "status", "iva_rate"}},
            }
            res = db.rest_insert("products", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"product": (res.get("data") or [{}])[0]}}

    def _list(self, db: SupabaseClient, company_id: str) -> dict:
        res = db.rest_select("products", filters={"company_id": f"eq.{company_id}"}, select="*", order="created_at.desc")
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        products = res.get("data") or []

        stock_res = db.rest_select("product_stock", filters={"company_id": f"eq.{company_id}"}, select="product_id,environment,current_stock")
        stock_by_product: dict[str, dict] = {}
        if stock_res.get("ok"):
            for row in stock_res.get("data") or []:
                stock_by_product.setdefault(row["product_id"], {})[row["environment"]] = row["current_stock"]
        for product in products:
            product["stock"] = stock_by_product.get(product["id"], {})

        return {"ok": True, "data": {"products": products}}
