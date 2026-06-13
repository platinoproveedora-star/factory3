from __future__ import annotations

import importlib.util
import re
from datetime import date, datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]


def _blank(value) -> str | None:
    text = str(value or "").strip()
    return text or None


def _money(value) -> float:
    return round(float(value or 0), 4)


class ErpVentasPedidoCreateService:
    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)
        items = context.get("items") or []
        if not isinstance(items, list) or not items:
            return {"ok": False, "error": "items requerido"}

        cfg_result = self._cfg(context)
        if not cfg_result.get("ok"):
            return cfg_result
        cfg = cfg_result["data"]
        base_context = {**context, **self._sales_context(context, cfg)}

        customer_result = self._get_or_create_customer(context, cfg)
        if not customer_result.get("ok"):
            return customer_result
        customer = customer_result.get("data", {}).get("customer") or {}
        customer_id = str(customer.get("id") or context.get("customer_id") or "").strip()
        if dry_run and not customer_id:
            customer_id = "customer-dryrun"
        if not customer_id:
            return {"ok": False, "error": "cliente invalido"}

        parsed, error = self._parse_items(context, cfg, items)
        if error:
            return {"ok": False, "error": error}

        subtotal = round(sum(row["line_subtotal"] for row in parsed), 2)
        tax_total = round(sum(row["vat_amount"] for row in parsed), 2)
        total = round(sum(row["line_total"] for row in parsed), 2)
        total_weight = round(sum(row["weight_kg_total"] or 0 for row in parsed), 4)

        doc_date = str(context.get("document_date") or date.today().isoformat())
        due_date = _blank(context.get("due_date") or context.get("promised_delivery_date"))
        payment_method = _blank(context.get("payment_method")) or "credit"
        delivery_address = _blank(context.get("delivery_address") or customer.get("address"))
        city = _blank(context.get("city"))
        city_quadrant = _blank(context.get("city_quadrant"))
        notes = _blank(context.get("notes"))
        external_folio = _blank(context.get("external_folio"))

        customer_name_snapshot = str(customer.get("party_name") or context.get("customer_name") or "").strip()
        customer_folio_snapshot = str(customer.get("folio") or "").strip()

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se guardo pedido",
                "data": {
                    "pedido": {
                        "folio": "PED-DRYRUN",
                        "customer_id": customer_id,
                        "customer_name_snapshot": customer_name_snapshot,
                        "subtotal": subtotal,
                        "tax_total": tax_total,
                        "total": total,
                        "total_weight_kg": total_weight,
                        "items_count": len(parsed),
                    }
                },
            }

        folio_result = self._reserve_pedido_folio(base_context)
        if not folio_result.get("ok"):
            return folio_result
        doc_folio = folio_result["data"]["folio"]

        doc_row = {
            "folio": doc_folio,
            "empresa_id": cfg["empresa_id"],
            "project_code": cfg["project_ventas"],
            "module_code": cfg["module_ventas"],
            "document_type": "pedido",
            "external_folio": external_folio,
            "customer_id": customer_id,
            "customer_name_snapshot": customer_name_snapshot,
            "customer_folio_snapshot": customer_folio_snapshot,
            "delivery_address": delivery_address,
            "chofer": None,
            "unidad": None,
            "driver_name": None,
            "vehicle_name": None,
            "payment_method": payment_method,
            "city": city,
            "city_quadrant": city_quadrant,
            "status": "pedido",
            "document_date": doc_date,
            "due_date": due_date,
            "currency": "MXN",
            "subtotal": subtotal,
            "discount_total": 0,
            "tax_total": tax_total,
            "total": total,
            "paid_total": 0,
            "balance_total": total,
            "total_weight_kg": total_weight,
            "notes": notes,
            "metadata": {
                "customer_schema": cfg["schema_inventario"],
                "customer_table": "erp_parties",
                "customer_id": customer_id,
                "logistics_pending": True,
            },
        }
        doc_result = SupabaseClient(base_context).rest_insert("sales_documents", doc_row)
        if not doc_result.get("ok"):
            return {"ok": False, "error": f"error al crear pedido: {doc_result.get('error')}"}
        doc_data = doc_result.get("data") or []
        saved_doc = doc_data[0] if isinstance(doc_data, list) and doc_data else doc_data
        doc_id = saved_doc.get("id") if isinstance(saved_doc, dict) else None
        if not doc_id:
            return {"ok": False, "error": "sales_documents no devolvio id"}

        saved_items = []
        for index, item in enumerate(parsed, start=1):
            item_folio_result = self._reserve_folio(base_context, "sales_document_items", "PEDI")
            if not item_folio_result.get("ok"):
                return item_folio_result
            item_folio = item_folio_result["data"]["folio"]
            item_row = {
                "folio": item_folio,
                "empresa_id": cfg["empresa_id"],
                "project_code": cfg["project_ventas"],
                "module_code": cfg["module_ventas"],
                "document_id": doc_id,
                "product_id": item.get("product_id"),
                "inventory_product_id": item.get("product_id"),
                "inventory_schema": cfg["schema_inventario"],
                "product_folio_snapshot": item.get("product_folio"),
                "product_name_snapshot": item.get("product_name") or item["description"],
                "description": item["description"],
                "quantity": item["quantity"],
                "unit": item["unit"],
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
                },
            }
            item_result = SupabaseClient(base_context).rest_insert("sales_document_items", item_row)
            if not item_result.get("ok"):
                return {"ok": False, "error": f"error al crear partida {index}: {item_result.get('error')}"}
            item_data = item_result.get("data") or []
            saved_item = item_data[0] if isinstance(item_data, list) and item_data else item_data
            saved_items.append({"id": saved_item.get("id") if isinstance(saved_item, dict) else None, "folio": item_folio})

        event_result = self._log_event(base_context, cfg, doc_id, doc_folio, customer_id, total, total_weight)
        if not event_result.get("ok"):
            return {"ok": False, "error": f"error al crear evento: {event_result.get('error')}"}

        return {
            "ok": True,
            "data": {
                "pedido": {
                    "id": doc_id,
                    "folio": doc_folio,
                    "customer_name_snapshot": customer_name_snapshot,
                    "subtotal": subtotal,
                    "tax_total": tax_total,
                    "total": total,
                    "total_weight_kg": total_weight,
                    "items": saved_items,
                }
            },
        }

    def _parse_items(self, context: dict, cfg: dict, items: list) -> tuple[list[dict], str | None]:
        parsed = []
        for idx, raw in enumerate(items, start=1):
            desc = str(raw.get("description") or raw.get("product_name") or "").strip()
            if not desc:
                return [], f"item {idx}: description requerido"
            try:
                qty = float(raw.get("quantity") or 0)
                vat_rate = float(raw.get("vat_rate") if raw.get("vat_rate") is not None else raw.get("tax_rate") if raw.get("tax_rate") is not None else 0.16)
            except (TypeError, ValueError):
                return [], f"item {idx}: quantity y vat_rate deben ser numericos"
            if qty <= 0:
                return [], f"item {idx}: quantity debe ser mayor a 0"
            price_mode = str(raw.get("price_mode") or "ex_vat").strip()
            try:
                if raw.get("unit_price_ex_vat") is not None:
                    unit_ex = float(raw.get("unit_price_ex_vat") or 0)
                elif raw.get("unit_price_inc_vat") is not None:
                    unit_ex = float(raw.get("unit_price_inc_vat") or 0) / (1 + vat_rate)
                    price_mode = "inc_vat"
                else:
                    unit_ex = float(raw.get("unit_price") or 0)
            except (TypeError, ValueError):
                return [], f"item {idx}: precio invalido"
            if unit_ex < 0:
                return [], f"item {idx}: precio no puede ser negativo"

            product = self._get_product(context, cfg, raw.get("product_id")) if raw.get("product_id") else {}
            weight_per_unit = product.get("weight_kg")
            weight_source = "catalog" if weight_per_unit is not None else "missing"
            weight_value = round(float(weight_per_unit or 0), 4)
            line_subtotal = round(qty * unit_ex, 4)
            vat_amount = round(line_subtotal * vat_rate, 4)
            unit_inc = round(unit_ex * (1 + vat_rate), 4)
            parsed.append(
                {
                    "product_id": raw.get("product_id"),
                    "product_folio": product.get("folio"),
                    "product_name": product.get("product_name"),
                    "description": product.get("product_name") or desc,
                    "quantity": qty,
                    "unit": str(raw.get("unit") or product.get("unit") or "pieza"),
                    "unit_price_ex_vat": round(unit_ex, 4),
                    "unit_price_inc_vat": unit_inc,
                    "vat_rate": vat_rate,
                    "vat_amount": vat_amount,
                    "line_subtotal": line_subtotal,
                    "line_total": round(line_subtotal + vat_amount, 4),
                    "weight_kg_per_unit": weight_value,
                    "weight_kg_total": round(weight_value * qty, 4),
                    "weight_source": weight_source,
                    "weight_unit": product.get("weight_unit"),
                    "price_mode": price_mode,
                }
            )
        return parsed, None

    def _cfg(self, context: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp" / "erp_project_context_resolve" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_project_context_resolve_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_project_context_resolve"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        resolve_context = {
            **context,
            "module_code": context.get("module_ventas") or context.get("module_code") or "ventas",
            "schema": context.get("schema_ventas") or context.get("sales_schema") or context.get("schema"),
        }
        result = module.ErpProjectContextResolveService().ejecutar(resolve_context)
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error") or "contexto ERP de ventas incompleto"}
        data = result.get("data") or {}
        module_projects = data.get("module_projects") if isinstance(data.get("module_projects"), dict) else {}
        cfg = {
            "empresa_id": data.get("empresa_id") or data.get("company_id"),
            "schema_ventas": data.get("sales_schema") or data.get("schema"),
            "schema_inventario": data.get("inventory_schema") or context.get("schema_inventario"),
            "project_ventas": data.get("project_code"),
            "project_inv": context.get("project_inv") or context.get("inventory_project_code") or module_projects.get("inventario"),
            "module_ventas": data.get("module_code") or "ventas",
            "module_inv": context.get("module_inv") or context.get("inventory_module_code") or "inventario",
        }
        missing = [key for key, value in cfg.items() if not value]
        if missing:
            return {"ok": False, "error": f"contexto ERP de ventas incompleto: {', '.join(missing)}"}
        return {"ok": True, "data": cfg}

    def _sales_context(self, context: dict, cfg: dict) -> dict:
        return {**context, "schema": cfg["schema_ventas"], "company_id": cfg["empresa_id"], "empresa_id": cfg["empresa_id"], "project_code": cfg["project_ventas"], "module_code": cfg["module_ventas"]}

    def _inventory_context(self, context: dict, cfg: dict) -> dict:
        return {**context, "schema": cfg["schema_inventario"], "company_id": cfg["empresa_id"], "empresa_id": cfg["empresa_id"], "project_code": cfg["project_inv"], "module_code": cfg["module_inv"]}

    def _get_or_create_customer(self, context: dict, cfg: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_ventas" / "erp_ventas_customer_get_or_create" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_ventas_customer_get_or_create_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_ventas_customer_get_or_create"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpVentasCustomerGetOrCreateService().ejecutar(self._inventory_context(context, cfg))

    def _get_product(self, context: dict, cfg: dict, product_id: str | None) -> dict:
        if not product_id:
            return {}
        result = SupabaseClient(self._inventory_context(context, cfg)).rest_select(
            "erp_products",
            filters={"id": f"eq.{product_id}", "active": "eq.true"},
            select="id,folio,product_name,unit,category,weight_kg,weight_unit",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if result.get("ok") and rows else {}

    def _reserve_folio(self, context: dict, table: str, prefix: str, digits: int = 5) -> dict:
        result = SupabaseClient(context).rest_select(table, filters={"folio": f"ilike.{prefix}-%"}, select="folio", limit=10000)
        if not result.get("ok"):
            return result
        max_num = 0
        for row in result.get("data") or []:
            match = re.match(rf"^{re.escape(prefix)}-(\d+)$", str(row.get("folio") or ""))
            if match:
                max_num = max(max_num, int(match.group(1)))
        return {"ok": True, "data": {"folio": f"{prefix}-{max_num + 1:0{digits}d}"}}

    def _reserve_pedido_folio(self, context: dict, digits: int = 5) -> dict:
        return self._reserve_folio(context, "sales_documents", "PED", digits)

    def _log_event(self, ctx: dict, cfg: dict, doc_id: str, doc_folio: str, customer_id: str, total: float, total_weight: float) -> dict:
        folio_num = re.sub(r"[^0-9]", "", doc_folio) or str(int(datetime.now(timezone.utc).timestamp()))
        return SupabaseClient(ctx).rest_insert(
            "sales_events",
            {
                "folio": f"EVT-PED-{folio_num}",
                "empresa_id": cfg["empresa_id"],
                "project_code": cfg["project_ventas"],
                "module_code": cfg["module_ventas"],
                "event_type": "pedido_created",
                "document_id": doc_id,
                "customer_id": customer_id,
                "payload": {"folio": doc_folio, "total": total, "total_weight_kg": total_weight},
            },
        )
