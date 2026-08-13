from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


class CfdiDocumentListService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        filters = {"company_id": f"eq.{company_id}"}
        if context.get("direction"):
            filters["direction"] = f"eq.{str(context['direction']).strip().lower()}"
        if context.get("status"):
            filters["status"] = f"eq.{str(context['status']).strip().lower()}"

        db = SupabaseClient({**context, "schema": _SCHEMA})
        limit = int(context.get("limit") or 100)
        res = db.rest_select("cfdi_documents", filters=filters, select="*", order="created_at.desc", limit=limit)
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"cfdi_documents": res.get("data") or []}}
