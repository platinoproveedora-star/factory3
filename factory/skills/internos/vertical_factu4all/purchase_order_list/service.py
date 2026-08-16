from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


class PurchaseOrderListService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        status = str(context.get("status") or "pending_xml").strip()
        db = SupabaseClient({**context, "schema": _SCHEMA})
        filters = {"company_id": f"eq.{company_id}", "source_type": "eq.purchase_order"}
        if status:
            filters["status"] = f"eq.{status}"
        res = db.rest_select("cfdi_documents", filters=filters, select="*", order="created_at.desc", limit=200)
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"purchase_orders": res.get("data") or []}}
