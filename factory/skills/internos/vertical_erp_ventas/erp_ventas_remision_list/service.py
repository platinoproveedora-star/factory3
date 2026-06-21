from __future__ import annotations
from datetime import datetime
from factory.engine import SupabaseClient


class ErpVentasRemisionListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._sales_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        limit = min(int(context.get("limit") or 100), 500)
        start_date = str(context.get("start_date") or "").strip()
        end_date = str(context.get("end_date") or "").strip()

        if start_date and end_date:
            start = self._as_date(start_date)
            end = self._as_date(end_date)
            if not start or not end:
                return {"ok": False, "error": "rango de fechas invalido"}
            if (end - start).days > 90:
                return {"ok": False, "error": "el rango maximo permitido es de 90 dias"}

        filters: dict = {"document_type": "eq.remision"}
        if start_date:
            filters["document_date"] = f"gte.{start_date}"
        if context.get("customer_id"):
            filters["customer_id"] = f"eq.{context['customer_id']}"
        if context.get("status"):
            filters["status"] = f"eq.{context['status']}"

        result = SupabaseClient(ctx).rest_select(
            "sales_documents",
            filters=filters,
            select="id,folio,external_folio,customer_id,customer_name_snapshot,status,document_date,delivery_address,chofer,unidad,total,balance_total,notes,created_at",
            order="document_date.desc,created_at.desc",
            limit=2000,
        )
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        if end_date:
            rows = [r for r in rows if str(r.get("document_date") or "")[:10] <= end_date]
        return {"ok": True, "data": {"remisiones": rows[:limit]}}

    def _as_date(self, value: str):
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            return None

    def _sales_context(self, context: dict) -> dict:
        schema = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_ventas/sales_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
