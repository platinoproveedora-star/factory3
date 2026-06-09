from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]


class ErpVentasRemisionCancelService:
    def ejecutar(self, context: dict) -> dict:
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}

        cfg = self._context(context)
        if not cfg.get("ok"):
            return cfg
        cfg = cfg["data"]

        sales_db = SupabaseClient(self._sales_context(context, cfg))
        doc = self._get_doc(sales_db, doc_id, folio)
        if not doc:
            return {"ok": False, "error": "remision no encontrada"}
        items_res = sales_db.rest_select(
            "sales_document_items",
            filters={"document_id": doc["id"]},
            select="id,folio,product_id,inventory_product_id,description,quantity,unit,unit_price,lot_code,line_total",
            order="created_at.asc",
            limit=500,
        )
        if not items_res.get("ok"):
            return items_res
        items = items_res.get("data") or []

        inv_ctx = self._inventory_context(context, cfg)
        inv_db = SupabaseClient(inv_ctx)
        existing = inv_db.rest_select(
            "erp_kardex",
            filters={"source_type": "ajuste"},
            select="id,metadata",
            limit=10000,
        )
        if not existing.get("ok"):
            return existing
        already_reversed = self._already_reversed(existing.get("data") or [], doc["id"], doc["folio"])
        if str(doc.get("status") or "") == "cancelada" and already_reversed:
            return {"ok": False, "error": "la remision ya tiene reversa de inventario"}

        now = datetime.now(timezone.utc).isoformat()
        note = self._blank(context.get("cancel_reason")) or "Cancelacion de remision"
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se cancelo remision",
                "data": {"remision": {**doc, "status": "cancelada"}, "items": items, "reversals_planned": len(items)},
            }

        reversals = []
        if not already_reversed:
            for item in items:
                product_id = item.get("inventory_product_id") or item.get("product_id")
                quantity = float(item.get("quantity") or 0)
                if not product_id or quantity <= 0:
                    continue
                movement = self._save_reversal(context, cfg, doc, item, product_id, quantity, note)
                if not movement.get("ok"):
                    return {"ok": False, "error": f"error revirtiendo item {item.get('folio') or item.get('id')}: {movement.get('error')}"}
                reversals.append(movement.get("data", {}).get("movement"))
        self._mark_original_outputs_canceled(inv_db, doc, note, now)

        update = {
            "status": "cancelada",
            "balance_total": 0,
            "updated_at": now,
            "notes": self._append_cancel_note(doc.get("notes"), note, now),
        }
        updated = sales_db.rest_update("sales_documents", update, {"id": doc["id"]})
        if not updated.get("ok"):
            return updated
        data = updated.get("data") or []
        remision = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"remision": remision, "reversals": reversals}}

    def _save_reversal(self, context: dict, cfg: dict, doc: dict, item: dict, product_id: str, quantity: float, note: str) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_inventory" / "erp_inventory_kardex_save" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_kardex_save_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_kardex_save"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryKardexSaveService().ejecutar(
            {
                **context,
                "schema": cfg["schema_inventario"],
                "project_code": cfg["project_inv"],
                "module_code": cfg["module_inv"],
                "dry_run": False,
                "source_type": "ajuste",
                "adjustment_direction": "entrada",
                "product_id": product_id,
                "product_name_snapshot": item.get("description"),
                "lot_code": item.get("lot_code"),
                "quantity": quantity,
                "unit_cost": 0,
                "unit_price": 0,
                "movement_date": datetime.now(timezone.utc).date().isoformat(),
                "notes": f"{note}: {doc.get('folio')} - {item.get('description')}",
                "metadata": {
                    "cancel_reason": note,
                    "cancels_source_type": "remision",
                    "cancels_remision_id": doc.get("id"),
                    "cancels_remision_folio": doc.get("folio"),
                    "cancels_remision_item_id": item.get("id"),
                    "cancels_remision_item_folio": item.get("folio"),
                    "original_lot_code": item.get("lot_code"),
                    "original_quantity_out": quantity,
                    "sales_schema": cfg["schema_ventas"],
                },
            }
        )

    def _get_doc(self, db: SupabaseClient, doc_id: str, folio: str) -> dict | None:
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        result = db.rest_select(
            "sales_documents",
            filters=filters,
            select="id,folio,external_folio,customer_id,customer_name_snapshot,status,document_date,delivery_address,total,balance_total,notes",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _already_reversed(self, rows: list[dict], doc_id: str, folio: str) -> bool:
        for row in rows:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if metadata.get("cancels_remision_id") == doc_id or metadata.get("cancels_remision_folio") == folio:
                return True
        return False

    def _mark_original_outputs_canceled(self, db: SupabaseClient, doc: dict, note: str, timestamp: str) -> None:
        result = db.rest_select(
            "erp_kardex",
            filters={"source_type": "remision", "source_folio": doc.get("folio")},
            select="id,metadata",
            limit=500,
        )
        if not result.get("ok"):
            return
        for row in result.get("data") or []:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            metadata.update(
                {
                    "canceled": True,
                    "canceled_at": timestamp,
                    "cancel_reason": note,
                    "canceled_by_skill": "vertical_erp_ventas/erp_ventas_remision_cancel",
                }
            )
            db.rest_update("erp_kardex", {"metadata": metadata}, {"id": row.get("id")})

    def _context(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        schema_ventas = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        schema_inventario = str(context.get("schema_inventario") or context.get("inventory_schema") or "").strip()
        project_ventas = str(context.get("sales_project_code") or context.get("project_ventas") or context.get("project_code") or "").strip()
        project_inv = str(context.get("inventory_project_code") or context.get("project_inv") or context.get("project_code") or "").strip()
        module_ventas = str(context.get("sales_module_code") or context.get("module_ventas") or "").strip()
        module_inv = str(context.get("inventory_module_code") or context.get("module_inv") or context.get("module_code") or "").strip()
        values = {
            "company_id": company_id,
            "schema_ventas": schema_ventas,
            "schema_inventario": schema_inventario,
            "project_ventas": project_ventas,
            "project_inv": project_inv,
            "module_ventas": module_ventas,
            "module_inv": module_inv,
        }
        missing = [key for key, value in values.items() if not value]
        if missing:
            return {"ok": False, "error": f"contexto ERP incompleto: {', '.join(missing)}"}
        return {"ok": True, "data": values}

    def _sales_context(self, context: dict, cfg: dict) -> dict:
        return {
            **context,
            "schema": cfg["schema_ventas"],
            "company_id": cfg["company_id"],
            "empresa_id": cfg["company_id"],
            "project_code": cfg["project_ventas"],
            "module_code": cfg["module_ventas"],
        }

    def _inventory_context(self, context: dict, cfg: dict) -> dict:
        return {
            **context,
            "schema": cfg["schema_inventario"],
            "company_id": cfg["company_id"],
            "empresa_id": cfg["company_id"],
            "project_code": cfg["project_inv"],
            "module_code": cfg["module_inv"],
        }

    def _append_cancel_note(self, previous: str | None, note: str, timestamp: str) -> str:
        suffix = f"Cancelada {timestamp}: {note}"
        previous = self._blank(previous)
        return f"{previous}\n{suffix}" if previous else suffix

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
