from __future__ import annotations

import importlib.util
import re
from datetime import date
from pathlib import Path

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[2]


class ErpVentasRemisionCreateService:
    def ejecutar(self, context: dict) -> dict:
        customer_id = str(context.get("customer_id") or "").strip()
        items = context.get("items") or []
        dry_run = context.get("dry_run", True)

        if not items or not isinstance(items, list):
            return {"ok": False, "error": "items requerido (lista con al menos 1 producto)"}

        customer_result = self._get_or_create_customer(context)
        if not customer_result.get("ok"):
            return customer_result
        customer = customer_result.get("data", {}).get("customer") or {}
        customer_id = str(customer.get("id") or customer_id).strip()
        if dry_run and not customer_id:
            customer_id = "customer-dryrun"
        if not customer_id:
            return {"ok": False, "error": "cliente invalido"}

        parsed_items, error = self._parse_items(items)
        if error:
            return {"ok": False, "error": error}

        subtotal = round(sum(i["line_subtotal"] for i in parsed_items), 2)
        tax_total = round(sum(i["tax_amount"] for i in parsed_items), 2)
        total = round(sum(i["line_total"] for i in parsed_items), 2)
        doc_date = str(context.get("document_date") or date.today().isoformat())
        external_folio = str(context.get("external_folio") or "").strip() or None
        notes = str(context.get("notes") or "").strip() or None
        customer_name_snapshot = str(customer.get("party_name") or "")
        customer_folio_snapshot = str(customer.get("folio") or "")
        delivery_address = str(context.get("delivery_address") or customer.get("address") or "").strip() or None

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se guardo remision",
                "data": {
                    "folio": "REM-DRYRUN",
                    "customer_name_snapshot": customer_name_snapshot,
                    "delivery_address": delivery_address,
                    "subtotal": subtotal,
                    "tax_total": tax_total,
                    "total": total,
                    "items_count": len(parsed_items),
                },
            }

        folio_result = self._reserve_remision_folio(context)
        if not folio_result.get("ok"):
            return folio_result
        doc_folio = folio_result["data"]["folio"]

        ctx_ventas = {**context, "schema": "uc101_proy002"}
        doc_row = {
            "folio": doc_folio,
            "empresa_id": "EMP_DURALON",
            "project_code": "PROY-002",
            "module_code": "ventas",
            "document_type": "remision",
            "external_folio": external_folio,
            "customer_id": customer_id,
            "customer_name_snapshot": customer_name_snapshot,
            "customer_folio_snapshot": customer_folio_snapshot,
            "delivery_address": delivery_address,
            "status": "emitida",
            "document_date": doc_date,
            "currency": "MXN",
            "subtotal": subtotal,
            "discount_total": 0,
            "tax_total": tax_total,
            "total": total,
            "paid_total": 0,
            "balance_total": total,
            "notes": notes,
            "metadata": {
                "customer_schema": "uc101_proy004",
                "customer_table": "erp_parties",
                "customer_id": customer_id,
            },
        }
        doc_result = SupabaseClient(ctx_ventas).rest_insert("sales_documents", doc_row)
        if not doc_result.get("ok"):
            return {"ok": False, "error": f"error al crear documento: {doc_result.get('error')}"}

        doc_data = doc_result.get("data") or []
        saved_doc = doc_data[0] if isinstance(doc_data, list) and doc_data else doc_data
        doc_id = saved_doc.get("id") if isinstance(saved_doc, dict) else None
        if not doc_id:
            return {"ok": False, "error": "sales_documents no devolvio id"}

        items_saved = []
        kardex_saved = []
        for index, item in enumerate(parsed_items, start=1):
            item_folio_result = self._reserve_folio(context, "sales_document_items", "REMI")
            if not item_folio_result.get("ok"):
                return item_folio_result
            item_folio = item_folio_result["data"]["folio"]
            product = self._get_product(context, item.get("product_id")) if item.get("product_id") else {}

            item_row = {
                "folio": item_folio,
                "empresa_id": "EMP_DURALON",
                "project_code": "PROY-002",
                "module_code": "ventas",
                "document_id": doc_id,
                "product_id": item.get("product_id"),
                "inventory_product_id": item.get("product_id"),
                "inventory_schema": "uc101_proy004",
                "product_folio_snapshot": product.get("folio"),
                "product_name_snapshot": product.get("product_name") or item["description"],
                "description": item["description"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "unit_price": item["unit_price"],
                "discount_amount": 0,
                "tax_rate": item["tax_rate"],
                "tax_amount": item["tax_amount"],
                "line_total": item["line_total"],
                "metadata": {
                    "inventory_schema": "uc101_proy004",
                    "inventory_product_id": item.get("product_id"),
                    "product_folio": product.get("folio"),
                    "line_index": index,
                },
            }
            item_result = SupabaseClient(ctx_ventas).rest_insert("sales_document_items", item_row)
            if not item_result.get("ok"):
                return {"ok": False, "error": f"error al crear item {index}: {item_result.get('error')}"}

            item_data = item_result.get("data") or []
            saved_item = item_data[0] if isinstance(item_data, list) and item_data else item_data
            item_id = saved_item.get("id") if isinstance(saved_item, dict) else None
            items_saved.append({"id": item_id, "folio": item_folio})

            if item.get("product_id"):
                k_result = self._kardex_salida(
                    context,
                    item,
                    doc_folio,
                    doc_id,
                    item_id,
                    item_folio,
                    customer_id,
                    customer_name_snapshot,
                    delivery_address,
                    doc_date,
                )
                if not k_result.get("ok"):
                    return {
                        "ok": False,
                        "error": f"error al crear kardex item {index}: {k_result.get('error')}",
                        "data": {"folio": doc_folio, "document_id": doc_id, "items": items_saved},
                    }
                kardex_saved.append(k_result.get("data", {}).get("movement"))

        event_result = self._log_event(ctx_ventas, doc_id, doc_folio, customer_id, total)
        if not event_result.get("ok"):
            return {"ok": False, "error": f"error al crear evento: {event_result.get('error')}"}

        return {
            "ok": True,
            "data": {
                "folio": doc_folio,
                "document_id": doc_id,
                "customer_name_snapshot": customer_name_snapshot,
                "subtotal": subtotal,
                "tax_total": tax_total,
                "total": total,
                "items": items_saved,
                "kardex": kardex_saved,
            },
        }

    def _get_or_create_customer(self, context: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_ventas" / "erp_ventas_customer_get_or_create" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_ventas_customer_get_or_create_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_ventas_customer_get_or_create"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpVentasCustomerGetOrCreateService().ejecutar(context)

    def _get_product(self, context: dict, product_id: str) -> dict:
        result = SupabaseClient({**context, "schema": "uc101_proy004"}).rest_select(
            "erp_products",
            filters={"id": f"eq.{product_id}"},
            select="id,folio,product_name,unit,category",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else {}

    def _parse_items(self, items: list) -> tuple[list, str | None]:
        parsed = []
        for idx, item in enumerate(items):
            desc = str(item.get("description") or item.get("product_name") or "").strip()
            if not desc:
                return [], f"item {idx + 1}: description requerido"
            try:
                qty = float(item.get("quantity") or 1)
                price = float(item.get("unit_price") or 0)
                tax_rate = float(item.get("tax_rate") or 0)
            except (ValueError, TypeError):
                return [], f"item {idx + 1}: quantity, unit_price y tax_rate deben ser numericos"
            if qty <= 0:
                return [], f"item {idx + 1}: quantity debe ser mayor a 0"
            if price < 0:
                return [], f"item {idx + 1}: unit_price no puede ser negativo"
            line_subtotal = round(qty * price, 4)
            tax_amount = round(line_subtotal * tax_rate, 4)
            line_total = round(line_subtotal + tax_amount, 4)
            parsed.append(
                {
                    "product_id": item.get("product_id"),
                    "description": desc,
                    "quantity": qty,
                    "unit": str(item.get("unit") or "pieza"),
                    "unit_price": price,
                    "tax_rate": tax_rate,
                    "tax_amount": tax_amount,
                    "line_subtotal": line_subtotal,
                    "line_total": line_total,
                }
            )
        return parsed, None

    def _reserve_folio(self, context: dict, table: str, prefix: str, digits: int = 5) -> dict:
        result = SupabaseClient({**context, "schema": "uc101_proy002"}).rest_select(
            table,
            filters={"folio": f"ilike.{prefix}-%"},
            select="folio",
            limit=10000,
        )
        if not result.get("ok"):
            return result
        max_num = 0
        for row in result.get("data") or []:
            match = re.match(rf"^{re.escape(prefix)}-(\d+)$", str(row.get("folio") or ""))
            if match:
                max_num = max(max_num, int(match.group(1)))
        return {"ok": True, "data": {"folio": f"{prefix}-{max_num + 1:0{digits}d}"}}

    def _reserve_remision_folio(self, context: dict, digits: int = 5) -> dict:
        max_num = 0
        sources = [
            (
                SupabaseClient({**context, "schema": "uc101_proy002"}).rest_select(
                    "sales_documents",
                    filters={"folio": "ilike.REM-%"},
                    select="folio",
                    limit=10000,
                ),
                "folio",
            ),
            (
                SupabaseClient({**context, "schema": "uc101_proy004"}).rest_select(
                    "erp_kardex",
                    filters={"source_folio": "ilike.REM-%"},
                    select="source_folio",
                    limit=10000,
                ),
                "source_folio",
            ),
        ]
        for result, column in sources:
            if not result.get("ok"):
                return result
            for row in result.get("data") or []:
                match = re.match(r"^REM-(\d+)$", str(row.get(column) or ""))
                if match:
                    max_num = max(max_num, int(match.group(1)))
        return {"ok": True, "data": {"folio": f"REM-{max_num + 1:0{digits}d}"}}

    def _kardex_salida(
        self,
        context: dict,
        item: dict,
        remision_folio: str,
        doc_id: str,
        item_id: str | None,
        item_folio: str,
        customer_id: str,
        customer_name: str,
        delivery_address: str | None,
        movement_date: str,
    ) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_inventory" / "erp_inventory_kardex_save" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_kardex_save_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_kardex_save"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryKardexSaveService().ejecutar(
            {
                **context,
                "schema": "uc101_proy004",
                "company_id": "EMP_DURALON",
                "project_code": "PROY-004",
                "module_code": "inventario",
                "dry_run": False,
                "allow_custom_folio": True,
                "product_id": item["product_id"],
                "product_name_snapshot": item["description"],
                "source_type": "remision",
                "source_folio": remision_folio,
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "total_sale": item["line_total"],
                "movement_date": movement_date,
                "party_id": customer_id,
                "party_name_snapshot": customer_name,
                "delivery_address": delivery_address,
                "notes": f"Remision {remision_folio} - {item['description']}",
                "metadata": {
                    "sales_schema": "uc101_proy002",
                    "remision_id": doc_id,
                    "remision_folio": remision_folio,
                    "remision_item_id": item_id,
                    "remision_item_folio": item_folio,
                },
            }
        )

    def _log_event(self, ctx: dict, doc_id: str, doc_folio: str, customer_id: str, total: float) -> dict:
        folio_num = re.sub(r"[^0-9]", "", doc_folio) or "0"
        return SupabaseClient(ctx).rest_insert(
            "sales_events",
            {
                "folio": f"EVT-REM-{folio_num}",
                "empresa_id": "EMP_DURALON",
                "project_code": "PROY-002",
                "module_code": "ventas",
                "event_type": "remision_created",
                "document_id": doc_id,
                "customer_id": customer_id,
                "payload": {"folio": doc_folio, "total": total},
            },
        )
