from __future__ import annotations
import re
from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")
_SORT_MAP = {
    "code": "sku",
    "name": "nombre",
    "created": "created_at",
}


class Coti4AllProductCatalogService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        active = context.get("active", None)
        is_active = None if active is None else bool(active)
        q = str(context.get("search") or context.get("query") or "").strip()
        category = str(context.get("category") or context.get("category_id") or "").strip()
        sort = str(context.get("sort") or "name").strip().lower()
        order_dir = str(context.get("order") or "asc").strip().lower()

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run — sin consulta Supabase",
                "data": {
                    "schema": ctx["schema"],
                    "active": is_active,
                    "search": q or None,
                    "category": category or None,
                    "sort": _SORT_MAP.get(sort, sort),
                    "order": order_dir,
                },
            }

        fields = "id,folio,empresa_id,project_code,module_code,sku,nombre,unidad,categoria,activo,costo_referencia,attributes,tags,created_at,updated_at"
        filters: dict[str, str] = {"activo": "eq.true"}
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if company_id:
            filters["empresa_id"] = f"eq.{company_id}"
        if is_active is False:
            filters["activo"] = "eq.false"
        if category:
            filters["categoria"] = f"eq.{category}"

        sort_expr = f"{_SORT_MAP.get(sort, 'nombre')}.{order_dir if order_dir in ('asc','desc') else 'asc'}"
        res = SupabaseClient(ctx).rest_select("catalog_items", filters=filters, select=fields, order=sort_expr)
        if not res.get("ok"):
            return res
        items = res.get("data") or []
        if q:
            ql = q.lower()
            items = [
                it
                for it in items
                if ql in str(it.get("nombre") or "").lower() or ql in str(it.get("sku") or "").lower()
            ]

        return {
            "ok": True,
            "schema": ctx["schema"],
            "meta": {"count": len(items), "query": q or None, "active": is_active, "sort": sort},
            "data": items,
        }

    def _tenant_context(self, context: dict) -> dict:
        schema = (
            str(context.get("schema") or context.get("company_schema") or context.get("schema_inventario") or "").strip()
        )
        if not schema or not _VALID_SCHEMA.match(schema):
            return {"ok": False, "error": "schema requerida y valida (ej: coti4all)"}
        context["schema"] = schema
        return {"ok": True, "data": context}
