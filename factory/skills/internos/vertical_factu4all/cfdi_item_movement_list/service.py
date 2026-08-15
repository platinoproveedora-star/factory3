from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


class CfdiItemMovementListService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        filters = {"company_id": f"eq.{company_id}"}
        if context.get("movement_direction"):
            filters["movement_direction"] = f"eq.{str(context['movement_direction']).strip().lower()}"
        if context.get("product_id"):
            filters["product_id"] = f"eq.{context['product_id']}"

        db = SupabaseClient({**context, "schema": _SCHEMA})
        limit = int(context.get("limit") or 200)
        res = db.rest_select("cfdi_item_movements", filters=filters, select="*", order="created_at.desc", limit=limit)
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"movements": res.get("data") or []}}
