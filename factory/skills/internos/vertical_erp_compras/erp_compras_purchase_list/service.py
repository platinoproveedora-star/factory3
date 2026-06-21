from __future__ import annotations

from datetime import datetime

from factory.engine import SupabaseClient


class ErpComprasPurchaseListService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._schema_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        limit = min(int(context.get("limit") or 20), 500)
        start_date = str(context.get("start_date") or "").strip()
        end_date = str(context.get("end_date") or "").strip()
        if start_date and end_date:
            start = self._as_date(start_date)
            end = self._as_date(end_date)
            if not start or not end:
                return {"ok": False, "error": "rango de fechas invalido"}
            if (end - start).days > 90:
                return {"ok": False, "error": "el rango maximo permitido es de 90 dias"}

        filters = {"source_type": "compra"}
        if start_date:
            filters["movement_date"] = f"gte.{start_date}"
        result = SupabaseClient(ctx).rest_select("erp_kardex", filters=filters, select="*", order="movement_date.desc,created_at.desc", limit=2000)
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        if end_date:
            rows = [row for row in rows if str(row.get("movement_date") or "")[:10] <= end_date]
        grouped = self._group(rows)
        return {"ok": True, "data": {"purchases": grouped[:limit], "movements": rows[:limit], "start_date": start_date or None, "end_date": end_date or None}}

    def _group(self, rows: list[dict]) -> list[dict]:
        purchases = {}
        order = []
        for row in rows:
            key = row.get("source_folio") or row.get("purchase_folio") or row.get("folio")
            if key not in purchases:
                order.append(key)
                purchases[key] = {
                    "source_folio": key,
                    "external_folio": row.get("external_folio"),
                    "supplier_id": row.get("supplier_id"),
                    "supplier_name_snapshot": row.get("supplier_name_snapshot"),
                    "movement_date": row.get("movement_date"),
                    "line_count": 0,
                    "total_cost": 0.0,
                    "paid_amount": 0.0,
                    "balance_amount": 0.0,
                    "payment_status": row.get("payment_status"),
                    "notes": row.get("notes"),
                    "canceled": False,
                    "items": [],
                }
            purchase = purchases[key]
            purchase["line_count"] += 1
            purchase["total_cost"] += float(row.get("total_cost") or 0)
            purchase["paid_amount"] += float(row.get("paid_amount") or 0)
            purchase["balance_amount"] += float(row.get("balance_amount") or 0)
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if metadata.get("canceled"):
                purchase["canceled"] = True
            purchase["items"].append(row)
        result = []
        for key in order:
            row = purchases[key]
            row["total_cost"] = round(row["total_cost"], 2)
            row["paid_amount"] = round(row["paid_amount"], 2)
            row["balance_amount"] = round(row["balance_amount"], 2)
            row["payment_status"] = "pagado" if row["balance_amount"] <= 0 and row["total_cost"] else "parcial" if row["paid_amount"] > 0 else "pendiente"
            result.append(row)
        return result

    def _as_date(self, value: str):
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            return None

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or context.get("inventory_schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema/supabase_schema requerido"}
        return {"ok": True, "data": {**context, "schema": schema}}
