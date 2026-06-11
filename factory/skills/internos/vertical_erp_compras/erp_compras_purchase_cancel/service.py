from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient

_SKILLS_ROOT = Path(__file__).resolve().parents[2]


class ErpComprasPurchaseCancelService:
    def ejecutar(self, context: dict) -> dict:
        source_folio = str(context.get("source_folio") or "").strip()
        if not source_folio:
            return {"ok": False, "error": "source_folio requerido"}

        ctx = self._schema_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        db = SupabaseClient(ctx)
        rows_res = db.rest_select(
            "erp_kardex",
            filters={"source_type": "compra", "source_folio": source_folio},
            select="*",
            order="created_at.asc",
            limit=500,
        )
        if not rows_res.get("ok"):
            return rows_res
        rows = rows_res.get("data") or []
        if not rows:
            return {"ok": False, "error": f"compra no encontrada: {source_folio}"}

        if self._already_canceled(rows):
            return {"ok": False, "error": "la compra ya fue cancelada"}

        note = str(context.get("cancel_reason") or "Cancelacion de compra").strip()

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se cancelo compra",
                "data": {"source_folio": source_folio, "reversals_planned": len(rows)},
            }

        now = datetime.now(timezone.utc).isoformat()
        reversals = []
        for row in rows:
            qty = float(row.get("quantity_in") or 0)
            if qty <= 0:
                continue
            result = self._save_reversal(ctx, row, qty, note, source_folio)
            if not result.get("ok"):
                return {"ok": False, "error": f"error revirtiendo renglon {row.get('folio')}: {result.get('error')}"}
            reversals.append(result["data"]["movement"])

        self._mark_canceled(db, rows, note, now)
        return {"ok": True, "data": {"source_folio": source_folio, "reversals": reversals}}

    def _save_reversal(self, ctx: dict, row: dict, quantity: float, note: str, source_folio: str) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_inventory" / "erp_inventory_kardex_save" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_kardex_save_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_kardex_save"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryKardexSaveService().ejecutar({
            **ctx,
            "dry_run": False,
            "source_type": "ajuste",
            "adjustment_direction": "salida",
            "product_id": row.get("product_id"),
            "product_name_snapshot": row.get("product_name_snapshot"),
            "lot_code": row.get("lot_code"),
            "quantity": quantity,
            "unit_cost": 0,
            "unit_price": 0,
            "movement_date": datetime.now(timezone.utc).date().isoformat(),
            "notes": f"{note}: {source_folio}",
            "metadata": {
                "cancel_reason": note,
                "cancels_source_type": "compra",
                "cancels_source_folio": source_folio,
                "cancels_kardex_folio": row.get("folio"),
                "cancels_kardex_id": row.get("id"),
                "original_quantity_in": quantity,
                "original_lot_code": row.get("lot_code"),
                "canceled_by_skill": "vertical_erp_compras/erp_compras_purchase_cancel",
            },
        })

    def _mark_canceled(self, db: SupabaseClient, rows: list[dict], note: str, timestamp: str) -> None:
        for row in rows:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            metadata.update({
                "canceled": True,
                "canceled_at": timestamp,
                "cancel_reason": note,
                "canceled_by_skill": "vertical_erp_compras/erp_compras_purchase_cancel",
            })
            db.rest_update("erp_kardex", {"metadata": metadata}, {"id": row.get("id")})

    def _already_canceled(self, rows: list[dict]) -> bool:
        for row in rows:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if metadata.get("canceled"):
                return True
        return False

    def _schema_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("supabase_schema") or context.get("inventory_schema") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("project_code") or context.get("inventory_project_code") or "").strip()
        missing = [k for k, v in {"schema": schema, "company_id": company_id, "project_code": project_code}.items() if not v]
        if missing:
            return {"ok": False, "error": f"contexto ERP de compras incompleto: {', '.join(missing)}"}
        return {
            "ok": True,
            "data": {
                **context,
                "schema": schema,
                "company_id": company_id,
                "empresa_id": company_id,
                "project_code": project_code,
                "module_code": "compras",
            },
        }
