from __future__ import annotations

import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]
_CONVERTIBLE_STATUS = {"pedido", "liberado"}


class ErpVentasPedidoToRemisionService:
    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)
        pedido_id = str(context.get("pedido_id") or context.get("id") or context.get("document_id") or "").strip()
        pedido_folio = str(context.get("pedido_folio") or context.get("folio") or "").strip()
        if not pedido_id and not pedido_folio:
            return {"ok": False, "error": "pedido_id o pedido_folio requerido"}

        detail = self._pedido_detail().ejecutar({**context, "id": pedido_id, "folio": pedido_folio})
        if not detail.get("ok"):
            return detail
        pedido = detail["data"]["pedido"]
        items = detail["data"].get("items") or []
        if str(pedido.get("status") or "") not in _CONVERTIBLE_STATUS:
            return {"ok": False, "error": "pedido no convertible; ya esta remisionado, cancelado o bloqueado"}
        if not items:
            return {"ok": False, "error": "pedido sin partidas"}

        remision_items = []
        for item in items:
            remision_items.append(
                {
                    "product_id": item.get("inventory_product_id") or item.get("product_id"),
                    "description": item.get("description") or item.get("product_name_snapshot"),
                    "quantity": item.get("quantity"),
                    "unit": item.get("unit"),
                    "unit_price": item.get("unit_price_ex_vat") if item.get("unit_price_ex_vat") is not None else item.get("unit_price"),
                    "tax_rate": item.get("vat_rate") if item.get("vat_rate") is not None else item.get("tax_rate"),
                    "metadata": {
                        "source_pedido_id": pedido.get("id"),
                        "source_pedido_folio": pedido.get("folio"),
                        "source_pedido_item_id": item.get("id"),
                        "source_pedido_item_folio": item.get("folio"),
                    },
                }
            )

        remision_context = {
            **context,
            "dry_run": dry_run,
            "customer_id": pedido.get("customer_id"),
            "customer_name": pedido.get("customer_name_snapshot"),
            "document_date": context.get("document_date") or date.today().isoformat(),
            "delivery_address": context.get("delivery_address") or pedido.get("delivery_address"),
            "external_folio": context.get("external_folio"),
            "notes": context.get("notes") or pedido.get("notes"),
            "items": remision_items,
            "parent_document_id": pedido.get("id"),
            "root_document_id": pedido.get("root_document_id") or pedido.get("id"),
            "metadata": {
                "source_document_type": "pedido",
                "source_pedido_id": pedido.get("id"),
                "source_pedido_folio": pedido.get("folio"),
            },
        }
        remision = self._remision_create().ejecutar(remision_context)
        if not remision.get("ok"):
            return remision
        if dry_run:
            return {"ok": True, "message": "dry_run: no se creo remision ni se bloqueo pedido", "data": {"pedido": pedido, "remision": remision.get("data")}}

        rem_data = remision.get("data") or {}
        remision_folio = rem_data.get("folio")
        remision_id = rem_data.get("document_id")
        ctx = self._sales_context(context)
        if not ctx.get("ok"):
            return ctx
        db = SupabaseClient(ctx["data"])
        metadata = pedido.get("metadata") if isinstance(pedido.get("metadata"), dict) else {}
        history = metadata.get("remisiones_history") if isinstance(metadata.get("remisiones_history"), list) else []
        history.append({"folio": remision_folio, "id": remision_id, "status": "emitida", "created_at": datetime.now(timezone.utc).isoformat()})
        metadata.update(
            {
                "remision_folio": remision_folio,
                "remision_id": remision_id,
                "converted_to_remision_folio": remision_folio,
                "converted_to_remision_id": remision_id,
                "converted_at": datetime.now(timezone.utc).isoformat(),
                "remisiones_history": history,
            }
        )
        update = db.rest_update(
            "sales_documents",
            {"status": "remisionado", "metadata": metadata, "updated_at": datetime.now(timezone.utc).isoformat()},
            {"id": pedido["id"]},
        )
        if not update.get("ok"):
            return update
        rows = update.get("data") or []
        updated_pedido = rows[0] if isinstance(rows, list) and rows else rows
        return {"ok": True, "data": {"pedido": updated_pedido, "remision": rem_data}}

    def _sales_context(self, context: dict) -> dict:
        schema = str(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema_ventas/sales_schema requerido"}
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        return {"ok": True, "data": {**context, "schema": schema, "company_id": company_id, "empresa_id": company_id}}

    def _pedido_detail(self):
        return self._load("vertical_erp_ventas", "erp_ventas_pedido_detail", "ErpVentasPedidoDetailService")

    def _remision_create(self):
        return self._load("vertical_erp_ventas", "erp_ventas_remision_create", "ErpVentasRemisionCreateService")

    def _load(self, vertical: str, skill: str, class_name: str):
        service_path = _SKILLS_ROOT / vertical / skill / "service.py"
        spec = importlib.util.spec_from_file_location(f"{skill}_service", service_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"no se pudo cargar {skill}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, class_name)()
