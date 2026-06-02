from __future__ import annotations
from factory.engine import SupabaseClient


class ErpVentasRemisionListService:
    def ejecutar(self, context: dict) -> dict:
        ctx   = {**context, "schema": "uc101_proy002"}
        limit = int(context.get("limit") or 50)
        filters: dict = {"document_type": "eq.remision"}
        if context.get("customer_id"):
            filters["customer_id"] = f"eq.{context['customer_id']}"
        if context.get("status"):
            filters["status"] = f"eq.{context['status']}"

        result = SupabaseClient(ctx).rest_select(
            "sales_documents",
            filters=filters,
            select="id,folio,external_folio,customer_id,customer_name_snapshot,status,document_date,delivery_address,total,balance_total,notes,created_at",
            order="created_at.desc",
            limit=limit,
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"remisiones": result.get("data", [])}}
