from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]
_EDITABLE_STATUS = {"pedido", "liberado", "draft"}


def _blank(value) -> str | None:
    text = str(value or "").strip()
    return text or None


class ErpVentasPedidoUpdateService:
    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}
        items = context.get("items") or []
        if not isinstance(items, list) or not items:
            return {"ok": False, "error": "items requerido"}

        create_service = self._create_service()
        cfg_result = create_service._cfg(context)
        if not cfg_result.get("ok"):
            return cfg_result
        cfg = cfg_result["data"]
        sales_ctx = create_service._sales_context(context, cfg)
        db = SupabaseClient(sales_ctx)

        doc = self._get_doc(db, doc_id, folio)
        if not doc:
            return {"ok": False, "error": "pedido no encontrado"}
        if str(doc.get("status") or "") not in _EDITABLE_STATUS:
            return {"ok": False, "error": "pedido bloqueado; no se puede modificar si ya esta remisionado o cancelado"}

        customer_result = create_service._get_or_create_customer(context, cfg)
        if not customer_result.get("ok"):
            return customer_result
        customer = customer_result.get("data", {}).get("customer") or {}
        customer_id = str(customer.get("id") or context.get("customer_id") or doc.get("customer_id") or "").strip()
        if not customer_id:
            return {"ok": False, "error": "cliente invalido"}

        parsed, error = create_service._parse_items(context, cfg, items)
        if error:
            return {"ok": False, "error": error}

        subtotal = round(sum(row["line_subtotal"] for row in parsed), 2)
        tax_total = round(sum(row["vat_amount"] for row in parsed), 2)
        total = round(sum(row["line_total"] for row in parsed), 2)
        total_weight = round(sum(row["weight_kg_total"] or 0 for row in parsed), 4)
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        metadata = {**metadata, "updated_by_skill": "vertical_erp_ventas/erp_ventas_pedido_update"}

        update = {
            "external_folio": _blank(context.get("external_folio")),
            "customer_id": customer_id,
            "customer_name_snapshot": str(customer.get("party_name") or context.get("customer_name") or doc.get("customer_name_snapshot") or "").strip(),
            "customer_folio_snapshot": str(customer.get("folio") or doc.get("customer_folio_snapshot") or "").strip() or None,
            "delivery_address": _blank(context.get("delivery_address") or customer.get("address")),
            "payment_method": _blank(context.get("payment_method")) or "credit",
            "city": _blank(context.get("city")),
            "city_quadrant": _blank(context.get("city_quadrant")),
            "document_date": str(context.get("document_date") or doc.get("document_date") or ""),
            "due_date": _blank(context.get("due_date") or context.get("promised_delivery_date")),
            "subtotal": subtotal,
            "tax_total": tax_total,
            "total": total,
            "balance_total": total,
            "total_weight_kg": total_weight,
            "notes": _blank(context.get("notes")),
            "metadata": metadata,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if dry_run:
            return {"ok": True, "message": "dry_run: no se actualizo pedido", "data": {"pedido": {**doc, **update}, "items": parsed}}

        updated = db.rest_update("sales_documents", update, {"id": doc["id"]})
        if not updated.get("ok"):
            return updated
        deleted = db.rest_delete("sales_document_items", {"document_id": doc["id"]})
        if not deleted.get("ok"):
            return deleted

        saved_items = []
        for index, item in enumerate(parsed, start=1):
            folio_result = create_service._reserve_folio(sales_ctx, "sales_document_items", "PEDI")
            if not folio_result.get("ok"):
                return folio_result
            item_folio = folio_result["data"]["folio"]
            item_row = {
                "folio": item_folio,
                "empresa_id": cfg["empresa_id"],
                "project_code": cfg["project_ventas"],
                "module_code": cfg["module_ventas"],
                "document_id": doc["id"],
                "product_id": item.get("product_id"),
                "inventory_product_id": item.get("product_id"),
                "inventory_schema": cfg["schema_inventario"],
                "product_folio_snapshot": item.get("product_folio"),
                "product_name_snapshot": item.get("product_name") or item["description"],
                "description": item["description"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "lot_code": item.get("lot_code"),
                "unit_price": item["unit_price_ex_vat"],
                "unit_price_ex_vat": item["unit_price_ex_vat"],
                "vat_rate": item["vat_rate"],
                "vat_amount": item["vat_amount"],
                "unit_price_inc_vat": item["unit_price_inc_vat"],
                "line_subtotal": item["line_subtotal"],
                "discount_amount": 0,
                "tax_rate": item["vat_rate"],
                "tax_amount": item["vat_amount"],
                "line_total": item["line_total"],
                "weight_kg_per_unit": item["weight_kg_per_unit"],
                "weight_kg_total": item["weight_kg_total"],
                "weight_source": item["weight_source"],
                "metadata": {
                    "inventory_schema": cfg["schema_inventario"],
                    "inventory_product_id": item.get("product_id"),
                    "product_folio": item.get("product_folio"),
                    "line_index": index,
                    "price_mode": item["price_mode"],
                    "weight_unit": item.get("weight_unit"),
                    "lot_code": item.get("lot_code"),
                },
            }
            item_result = db.rest_insert("sales_document_items", item_row)
            if not item_result.get("ok"):
                return {"ok": False, "error": f"error al guardar partida {index}: {item_result.get('error')}"}
            rows = item_result.get("data") or []
            saved = rows[0] if isinstance(rows, list) and rows else rows
            saved_items.append({"id": saved.get("id") if isinstance(saved, dict) else None, "folio": item_folio})

        rows = updated.get("data") or []
        pedido = rows[0] if isinstance(rows, list) and rows else rows
        return {"ok": True, "data": {"pedido": pedido, "items": saved_items}}

    def _create_service(self):
        service_path = _SKILLS_ROOT / "vertical_erp_ventas" / "erp_ventas_pedido_create" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_ventas_pedido_create_service", service_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("no se pudo cargar erp_ventas_pedido_create")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpVentasPedidoCreateService()

    def _get_doc(self, db: SupabaseClient, doc_id: str, folio: str) -> dict | None:
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        result = db.rest_select(
            "sales_documents",
            filters={**filters, "document_type": "eq.pedido"},
            select="id,folio,customer_id,customer_name_snapshot,customer_folio_snapshot,status,document_date,metadata",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else None
