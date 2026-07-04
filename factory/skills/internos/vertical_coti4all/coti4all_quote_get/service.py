from __future__ import annotations
import re
from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")
_QUOTE_FIELDS = (
    "id,folio,empresa_id,client_nombre,client_email,status,moneda,"
    "subtotal,impuesto,total,costo_total,margen,margen_pct,"
    "validez_dias,notas,metadata,created_at,updated_at"
)
_ITEM_FIELDS = (
    "id,folio,sku,nombre,cantidad,unidad,precio_unitario,costo_unitario,"
    "line_subtotal,line_costo,line_margen,line_margen_pct,impuesto_pct,"
    "line_impuesto,line_total,notas,orden"
)


class Coti4AllQuoteGetService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        quote_id = str(context.get("quote_id") or context.get("id") or "").strip()
        folio = str(context.get("folio") or context.get("external_ref") or "").strip()
        if not quote_id and not folio:
            return {"ok": False, "error": "quote_id o folio requerido"}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run — sin consulta Supabase",
                "data": {"schema": ctx["schema"], "quote_id": quote_id or None, "folio": folio or None},
            }

        filters: dict[str, str] = {"empresa_id": f"eq.{ctx['company_id']}"}
        if quote_id:
            filters["id"] = f"eq.{quote_id}"
        if folio:
            filters["folio"] = f"eq.{folio}"

        res = SupabaseClient(ctx).rest_select("quotes", filters=filters, select=_QUOTE_FIELDS, limit=1)
        if not res.get("ok"):
            return res
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "cotizacion no encontrada"}
        quote = rows[0]

        items_res = SupabaseClient(ctx).rest_select(
            "quote_items",
            filters={"quote_id": f"eq.{quote['id']}"},
            select=_ITEM_FIELDS,
            order="orden.asc",
            limit=500,
        )
        if not items_res.get("ok"):
            return items_res
        items = items_res.get("data") or []

        metadata = quote.get("metadata") or {}
        dashboard_form = metadata.get("dashboard_form") if isinstance(metadata, dict) else None

        return {
            "ok": True,
            "schema": ctx["schema"],
            "data": {
                "quote": quote,
                "items": items,
                "dashboard_form": dashboard_form,
            },
        }

    def _tenant_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or "").strip()
        if not schema or not _VALID_SCHEMA.match(schema):
            return {"ok": False, "error": "schema requerida y valida (ej: coti4all)"}
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        context["schema"] = schema
        context.setdefault("company_id", company_id)
        return {"ok": True, "data": context}
