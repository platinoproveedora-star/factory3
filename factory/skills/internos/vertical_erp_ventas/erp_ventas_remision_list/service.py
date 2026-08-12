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
        rows = self._apply_inventory_cancellations(context, rows)
        if end_date:
            rows = [r for r in rows if str(r.get("document_date") or "")[:10] <= end_date]
        return {"ok": True, "data": {"remisiones": rows[:limit]}}

    def _apply_inventory_cancellations(self, context: dict, rows: list[dict]) -> list[dict]:
        inventory_schema = str(context.get("inventory_schema") or context.get("schema_inventario") or "").strip()
        if not inventory_schema or not rows:
            return rows
        result = SupabaseClient({**context, "schema": inventory_schema}).rest_select(
            "erp_kardex",
            select="source_type,source_folio,external_folio,metadata",
            limit=10000,
        )
        if not result.get("ok"):
            return rows

        canceled_folios = set()
        canceled_ids = set()
        for movement in result.get("data") or []:
            metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
            if movement.get("source_type") == "remision" and metadata.get("canceled"):
                canceled_folios.update(self._folio_keys(movement.get("source_folio")))
                canceled_folios.update(self._folio_keys(movement.get("external_folio")))
            cancels_folio = metadata.get("cancels_remision_folio")
            cancels_external = metadata.get("cancels_remision_external_folio")
            cancels_id = str(metadata.get("cancels_remision_id") or "").strip()
            canceled_folios.update(self._folio_keys(cancels_folio))
            canceled_folios.update(self._folio_keys(cancels_external))
            if cancels_id:
                canceled_ids.add(cancels_id)

        if not canceled_folios and not canceled_ids:
            return rows
        patched = []
        for row in rows:
            row_keys = self._folio_keys(row.get("folio")) | self._folio_keys(row.get("external_folio"))
            is_cancelled = bool(row_keys & canceled_folios) or str(row.get("id") or "") in canceled_ids
            if not is_cancelled:
                patched.append(row)
                continue
            notes = str(row.get("notes") or "").strip()
            patched.append(
                {
                    **row,
                    "status": "cancelada",
                    "balance_total": 0,
                    "notes": notes if notes.lower().startswith("cancelada ") else f"{notes}\nCancelada por inventario/kardex".strip(),
                }
            )
        return patched

    def _folio_keys(self, value) -> set[str]:
        raw = str(value or "").strip()
        if not raw:
            return set()
        upper = raw.upper()
        keys = {raw, upper}
        digits = "".join(ch for ch in upper if ch.isdigit())
        if digits:
            num = str(int(digits))
            keys.update({digits, num, f"REM-{num}", f"REM-{int(digits):05d}"})
        return keys

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
