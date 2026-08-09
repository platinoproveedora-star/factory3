from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import db, inventory_db, is_dry_run, now_iso, reserve_folio, resolve_context, table_filters  # noqa: E402


class LogisticsPurchaseOrderManageService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        action = str(context.get("action") or "create").strip()
        if action == "create":
            return self._create(ctx, context)
        if action == "update":
            return self._update(ctx, context)
        if action == "cancel":
            return self._status(ctx, context, "cancelado")
        if action == "convert_to_purchase":
            return self._convert_to_purchase(ctx, context)
        return {"ok": False, "error": "action invalida"}

    def _create(self, ctx: dict, context: dict) -> dict:
        items_result = self._items(ctx, context.get("items"))
        if not items_result.get("ok"):
            return items_result
        supplier = self._supplier(ctx, context.get("supplier_id"), context.get("supplier_name"))
        summary = self._summary(items_result["data"]["items"])
        folio = {"ok": True, "data": {"folio": "PCO-DRYRUN"}} if is_dry_run(context) else reserve_folio(ctx, "logistics_purchase_orders", "PCO")
        if not folio.get("ok"):
            return folio
        row = {
            "folio": folio["data"]["folio"],
            "empresa_id": ctx["company_id"],
            "project_code": ctx["project_code"],
            "module_code": ctx["module_code"],
            "supplier_id": supplier.get("id"),
            "supplier_name": supplier.get("name"),
            "pickup_address": _blank(context.get("pickup_address")),
            "fecha_recoleccion": _blank(context.get("fecha_recoleccion") or context.get("fecha_entrega")),
            "status": str(context.get("status") or "pendiente"),
            "total_weight_kg": summary["weight"],
            "subtotal": summary["subtotal"],
            "tax_total": summary["tax"],
            "total": summary["total"],
            "items": items_result["data"]["items"],
            "notes": _blank(context.get("notes")),
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
            "created_by_user_id": context.get("user_id") or context.get("created_by_user_id"),
        }
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se creo pedido compra", "data": {"purchase_order": row}}
        result = db(ctx).rest_insert("logistics_purchase_orders", row)
        return result if not result.get("ok") else {"ok": True, "data": {"purchase_order": (result.get("data") or [{}])[0]}}

    def _update(self, ctx: dict, context: dict) -> dict:
        order = self._purchase_order(ctx, context)
        if not order:
            return {"ok": False, "error": "pedido compra no encontrado"}
        update: dict[str, Any] = {"updated_at": now_iso()}
        for key in ["supplier_id", "supplier_name", "pickup_address", "fecha_recoleccion", "notes", "status"]:
            if key in context:
                update[key] = context.get(key) or None
        if "items" in context:
            items_result = self._items(ctx, context.get("items"))
            if not items_result.get("ok"):
                return items_result
            summary = self._summary(items_result["data"]["items"])
            update.update({"items": items_result["data"]["items"], "total_weight_kg": summary["weight"], "subtotal": summary["subtotal"], "tax_total": summary["tax"], "total": summary["total"]})
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se actualizo pedido compra", "data": {"purchase_order": {**order, **update}}}
        result = db(ctx).rest_update("logistics_purchase_orders", update, table_filters(ctx, {"id": f"eq.{order['id']}"}))
        return result if not result.get("ok") else {"ok": True, "data": {"purchase_order": (result.get("data") or [{}])[0]}}

    def _status(self, ctx: dict, context: dict, status: str) -> dict:
        order = self._purchase_order(ctx, context)
        if not order:
            return {"ok": False, "error": "pedido compra no encontrado"}
        update = {"status": status, "updated_at": now_iso()}
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se actualizo status", "data": update}
        return db(ctx).rest_update("logistics_purchase_orders", update, table_filters(ctx, {"id": f"eq.{order['id']}"}))

    def _convert_to_purchase(self, ctx: dict, context: dict) -> dict:
        order = self._purchase_order(ctx, context)
        if not order:
            return {"ok": False, "error": "pedido compra no encontrado"}
        if order.get("purchase_folio"):
            return {"ok": False, "error": "pedido compra ya convertido"}
        supplier_id = _blank(order.get("supplier_id") or context.get("supplier_id"))
        if not supplier_id:
            return {"ok": False, "error": "supplier_id requerido para convertir a compra"}
        items = order.get("items") if isinstance(order.get("items"), list) else []
        purchase_items = []
        for index, item in enumerate(items, start=1):
            product_id = _blank((item or {}).get("product_id"))
            quantity = float((item or {}).get("quantity") or 0)
            unit_cost = float((item or {}).get("unit_cost") or 0)
            if not product_id:
                return {"ok": False, "error": f"producto requerido en renglon {index}"}
            if quantity <= 0:
                return {"ok": False, "error": f"cantidad requerida en renglon {index}"}
            if unit_cost <= 0:
                return {"ok": False, "error": f"precio/costo requerido en renglon {index}"}
            purchase_items.append({"product_id": product_id, "quantity": quantity, "unit_cost": unit_cost, "tax_rate": float((item or {}).get("tax_rate") or 0), "notes": (item or {}).get("notes")})
        service = self._purchase_create_service()
        purchase_result = service.ejecutar(
            {
                **ctx,
                "schema": ctx.get("inventory_schema"),
                "project_code": ctx.get("inventory_project_code"),
                "module_code": "compras",
                "supplier_id": supplier_id,
                "items": purchase_items,
                "movement_date": context.get("movement_date") or order.get("fecha_recoleccion"),
                "notes": context.get("notes") or order.get("notes"),
                "metadata": {"logistics_purchase_order_id": order.get("id"), "logistics_purchase_order_folio": order.get("folio")},
                "dry_run": context.get("dry_run", True),
            }
        )
        if not purchase_result.get("ok"):
            return purchase_result
        purchase = (purchase_result.get("data") or {}).get("purchase") or {}
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se convirtio pedido compra", "data": {"purchase": purchase, "purchase_order": order}}
        update = {"status": "convertido", "purchase_folio": purchase.get("source_folio"), "updated_at": now_iso()}
        updated = db(ctx).rest_update("logistics_purchase_orders", update, table_filters(ctx, {"id": f"eq.{order['id']}"}))
        if not updated.get("ok"):
            return updated
        return {"ok": True, "data": {"purchase": purchase, "purchase_order": (updated.get("data") or [{}])[0]}}

    def _purchase_order(self, ctx: dict, context: dict) -> dict | None:
        row_id = _blank(context.get("purchase_order_id") or context.get("id"))
        folio = _blank(context.get("purchase_order_folio") or context.get("folio"))
        if not row_id and not folio:
            return None
        filters = {"id": f"eq.{row_id}"} if row_id else {"folio": f"eq.{folio}"}
        result = db(ctx).rest_select("logistics_purchase_orders", filters=table_filters(ctx, filters), select="*", limit=1)
        rows = result.get("data") or [] if result.get("ok") else []
        return rows[0] if rows else None

    def _items(self, ctx: dict, raw: Any) -> dict:
        if not isinstance(raw, list) or not raw:
            return {"ok": False, "error": "items requerido"}
        products = self._products(ctx)
        rows = []
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            product_id = _blank(item.get("product_id"))
            product = products.get(product_id, {})
            name = _blank(item.get("product_name_snapshot") or product.get("product_name") or item.get("description"))
            quantity = float(item.get("quantity") or 0)
            unit_cost = float(item.get("unit_cost") or 0)
            tax_rate = float(item.get("tax_rate") or 0)
            if tax_rate in {8.0, 16.0}:
                tax_rate = tax_rate / 100
            if quantity <= 0:
                return {"ok": False, "error": f"cantidad invalida en renglon {index}"}
            subtotal = round(quantity * unit_cost, 2)
            tax = round(subtotal * tax_rate, 2)
            weight = round(quantity * float(product.get("weight_kg") or item.get("weight_kg") or 0), 4)
            rows.append(
                {
                    "product_id": product_id,
                    "product_folio_snapshot": product.get("folio") or item.get("product_folio_snapshot"),
                    "product_name_snapshot": name,
                    "description": name,
                    "quantity": quantity,
                    "unit": item.get("unit") or product.get("unit"),
                    "unit_cost": unit_cost,
                    "tax_rate": tax_rate,
                    "line_total": round(subtotal + tax, 2),
                    "weight_kg_total": weight,
                    "notes": _blank(item.get("notes")),
                }
            )
        return {"ok": True, "data": {"items": rows}}

    def _summary(self, items: list[dict]) -> dict:
        subtotal = round(sum(float(item.get("quantity") or 0) * float(item.get("unit_cost") or 0) for item in items), 2)
        total = round(sum(float(item.get("line_total") or 0) for item in items), 2)
        return {"weight": round(sum(float(item.get("weight_kg_total") or 0) for item in items), 4), "subtotal": subtotal, "tax": round(total - subtotal, 2), "total": total}

    def _supplier(self, ctx: dict, supplier_id: Any, supplier_name: Any) -> dict:
        supplier_id = _blank(supplier_id)
        if not supplier_id:
            return {"id": None, "name": _blank(supplier_name)}
        inv = inventory_db(ctx)
        if inv is None:
            return {"id": supplier_id, "name": _blank(supplier_name)}
        result = inv.rest_select("erp_parties", filters={"id": f"eq.{supplier_id}"}, select="id,party_name,address", limit=1)
        rows = result.get("data") or [] if result.get("ok") else []
        return {"id": supplier_id, "name": rows[0].get("party_name") if rows else _blank(supplier_name)}

    def _products(self, ctx: dict) -> dict[str, dict]:
        inv = inventory_db(ctx)
        if inv is None:
            return {}
        result = inv.rest_select("erp_products", filters={"active": "neq.false"}, select="id,folio,product_name,unit,weight_kg", limit=2000)
        return {str(row.get("id")): row for row in (result.get("data") or [])} if result.get("ok") else {}

    def _purchase_create_service(self):
        service_path = Path(__file__).resolve().parents[2] / "vertical_erp_compras" / "erp_compras_purchase_create" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_compras_purchase_create_service", service_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("no se pudo cargar erp_compras_purchase_create")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpComprasPurchaseCreateService()


def _blank(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
