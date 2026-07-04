from __future__ import annotations
import re
from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


class Coti4AllPriceListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        product_id = str(context.get("product_id") or context.get("id") or context.get("product_code") or context.get("sku") or "").strip()
        price_list_id = str(context.get("price_list_id") or "").strip()

        if not product_id and not price_list_id:
            res = SupabaseClient(ctx).rest_select(
                "price_lists",
                filters={"activo": "eq.true"},
                select="id,folio,empresa_id,project_code,module_code,nombre,prioridad,moneda,activo,created_at,updated_at",
                order="prioridad.asc",
                limit=100,
            )
            if not res.get("ok"):
                return res
            return {"ok": True, "schema": ctx["schema"], "data": {"price_lists": res.get("data") or []}}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run — sin consulta Supabase",
                "data": {"schema": ctx["schema"], "product_id": product_id or None, "price_list_id": price_list_id or None},
            }

        try:
            sku = self._resolve_sku(ctx, product_id) if product_id else None
            filters = {"activo": "eq.true"}
            if sku:
                filters["sku"] = f"eq.{sku}"
            res = SupabaseClient(ctx).rest_select(
                "price_list_items",
                filters=filters,
                select="id,folio,price_list_id,empresa_id,sku,precio,moneda,activo,created_at,updated_at",
                order="created_at.desc",
                limit=100,
            )
            rows = res.get("data") or []
            if price_list_id:
                rows = [r for r in rows if str(r.get("price_list_id")).lower() == price_list_id.lower()]
            return {"ok": True, "schema": ctx["schema"], "data": {"prices": rows}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _tenant_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("company_schema") or "").strip()
        if not schema or not _VALID_SCHEMA.match(schema):
            return {"ok": False, "error": "schema requerida y valida (ej: coti4all)"}
        context["schema"] = schema
        return {"ok": True, "data": context}

    def _resolve_sku(self, ctx: dict, value: str) -> str | None:
        if re.match(r"^[0-9a-fA-F-]{36}$", value):
            res = SupabaseClient(ctx).rest_select("catalog_items", filters={"id": f"eq.{value}"}, select="sku", limit=1)
            rows = res.get("data") or []
            return rows[0].get("sku") if rows else None
        res = SupabaseClient(ctx).rest_select(
            "catalog_items", filters={"sku": f"eq.{value}", "activo": "eq.true"}, select="sku", limit=1
        )
        rows = res.get("data") or []
        return rows[0].get("sku") if rows else value
