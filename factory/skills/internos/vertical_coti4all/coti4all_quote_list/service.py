from __future__ import annotations
import re
from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")
_FIELDS = (
    "id,folio,empresa_id,client_nombre,client_email,status,moneda,"
    "subtotal,impuesto,total,costo_total,margen,margen_pct,"
    "validez_dias,notas,created_at,updated_at"
)


class Coti4AllQuoteListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        q = str(context.get("search") or context.get("query") or "").strip()
        status = str(context.get("status") or "").strip()
        limit = int(context.get("limit") or 100)

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run — sin consulta Supabase",
                "data": {"schema": ctx["schema"], "search": q or None, "status": status or None, "limit": limit},
            }

        filters: dict[str, str] = {"empresa_id": f"eq.{ctx['company_id']}"}
        if status:
            filters["status"] = f"eq.{status}"

        res = SupabaseClient(ctx).rest_select(
            "quotes",
            filters=filters,
            select=_FIELDS,
            order="created_at.desc",
            limit=limit,
        )
        if not res.get("ok"):
            return res
        rows = res.get("data") or []
        if q:
            ql = q.lower()
            rows = [
                row
                for row in rows
                if ql in str(row.get("folio") or "").lower() or ql in str(row.get("client_nombre") or "").lower()
            ]

        return {
            "ok": True,
            "schema": ctx["schema"],
            "meta": {"count": len(rows), "search": q or None, "status": status or None},
            "data": rows,
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
