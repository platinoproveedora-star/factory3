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

        cfg_result = self._cfg(context)
        if not cfg_result.get("ok"):
            return cfg_result
        cfg = cfg_result["data"]
        context = {**context, **self._sales_context(context, cfg)}

        customer_result = self._get_or_create_customer(context, cfg)
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
        parsed_items, error = self._enrich_cost_snapshots(context, cfg, parsed_items, dry_run)
        if error:
            return {"ok": False, "error": error}

        subtotal = round(sum(i["line_subtotal"] for i in parsed_items), 2)
        tax_total = round(sum(i["tax_amount"] for i in parsed_items), 2)
        total = round(sum(i["line_total"] for i in parsed_items), 2)
        doc_date = str(context.get("document_date") or date.today().isoformat())
        external_folio = str(context.get("external_folio") or "").strip() or None
        notes = str(context.get("notes") or "").strip() or None
        chofer = str(context.get("chofer") or context.get("driver") or "").strip() or None
        unidad = str(context.get("unidad") or context.get("vehicle_unit") or "").strip() or None
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
                    "chofer": chofer,
                    "unidad": unidad,
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

        mark_as_paid = bool(context.get("mark_as_paid", False))
        paid_total   = total if mark_as_paid else 0
        balance_doc  = 0 if mark_as_paid else total
        doc_status   = "pagada" if mark_as_paid else "emitida"

        ctx_ventas = self._sales_context(context, cfg)
        doc_row = {
            "folio": doc_folio,
            "empresa_id": cfg["empresa_id"],
            "project_code": cfg["project_ventas"],
            "module_code": cfg["module_ventas"],
            "document_type": "remision",
            "external_folio": external_folio,
            "customer_id": customer_id,
            "customer_name_snapshot": customer_name_snapshot,
            "customer_folio_snapshot": customer_folio_snapshot,
            "delivery_address": delivery_address,
            "chofer": chofer,
            "unidad": unidad,
            "status": doc_status,
            "document_date": doc_date,
            "currency": "MXN",
            "subtotal": subtotal,
            "discount_total": 0,
            "tax_total": tax_total,
            "total": total,
            "paid_total": paid_total,
            "balance_total": balance_doc,
            "notes": notes,
            "metadata": {
                "customer_schema": cfg["schema_inventario"],
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
            product = self._get_product(context, cfg, item.get("product_id")) if item.get("product_id") else {}

            item_row = {
                "folio": item_folio,
                "empresa_id": cfg["empresa_id"],
                "project_code": cfg["project_ventas"],
                "module_code": cfg["module_ventas"],
                "document_id": doc_id,
                "product_id": item.get("product_id"),
                "inventory_product_id": item.get("product_id"),
                "inventory_schema": cfg["schema_inventario"],
                "product_folio_snapshot": product.get("folio"),
                "product_name_snapshot": product.get("product_name") or item["description"],
                "description": item["description"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "unit_price": item["unit_price"],
                "lot_code": item.get("lot_code"),
                "lot_cost_snapshot": item.get("lot_cost_snapshot"),
                "avg_cost_snapshot": item.get("avg_cost_snapshot"),
                "last_cost_snapshot": item.get("last_cost_snapshot"),
                "discount_amount": 0,
                "tax_rate": item["tax_rate"],
                "tax_amount": item["tax_amount"],
                "line_total": item["line_total"],
                "metadata": {
                    "inventory_schema": cfg["schema_inventario"],
                    "inventory_product_id": item.get("product_id"),
                    "product_folio": product.get("folio"),
                    "line_index": index,
                    "lot_code": item.get("lot_code"),
                    "line_subtotal": item.get("line_subtotal"),
                    "tax_rate": item.get("tax_rate"),
                    "tax_amount": item.get("tax_amount"),
                    "line_total": item.get("line_total"),
                    "lot_unit_cost": item.get("lot_cost_snapshot"),
                    "last_purchase_cost": item.get("last_cost_snapshot"),
                    "weighted_avg_cost": item.get("weighted_avg_cost_snapshot"),
                    "weighted_avg_cost_after_sale": item.get("avg_cost_snapshot"),
                    "lot_cost_snapshot": item.get("lot_cost_snapshot"),
                    "avg_cost_snapshot": item.get("avg_cost_snapshot"),
                    "last_cost_snapshot": item.get("last_cost_snapshot"),
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
                    cfg,
                    item,
                    doc_folio,
                    doc_id,
                    item_id,
                    item_folio,
                    customer_id,
                    customer_name_snapshot,
                    delivery_address,
                    doc_date,
                    notes,
                    paid_amount=item["line_total"] if mark_as_paid else 0,
                )
                if not k_result.get("ok"):
                    return {
                        "ok": False,
                        "error": f"error al crear kardex item {index}: {k_result.get('error')}",
                        "data": {"folio": doc_folio, "document_id": doc_id, "items": items_saved},
                    }
                kardex_saved.append(k_result.get("data", {}).get("movement"))

        event_result = self._log_event(ctx_ventas, cfg, doc_id, doc_folio, customer_id, total)
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
        issues = []
        cfg = {
            "empresa_id": data.get("empresa_id") or data.get("company_id"),
            "schema_ventas": data.get("sales_schema") or data.get("schema"),
            "schema_inventario": data.get("inventory_schema") or context.get("schema_inventario"),
            "project_ventas": data.get("project_code"),
            "project_inv": context.get("project_inv") or context.get("inventory_project_code") or module_projects.get("inventario"),
            "module_ventas": data.get("module_code") or "ventas",
            "module_inv": context.get("module_inv") or context.get("inventory_module_code") or "inventario",
        }
        for key in ("empresa_id", "schema_ventas", "schema_inventario", "project_ventas", "project_inv", "module_ventas", "module_inv"):
            if not cfg.get(key):
                issues.append(key)
        if issues:
            return {"ok": False, "error": f"contexto ERP de ventas incompleto: {', '.join(issues)}"}
        return {"ok": True, "data": cfg}

    def _sales_context(self, context: dict, cfg: dict) -> dict:
        return {
            **context,
            "schema": cfg["schema_ventas"],
            "company_id": cfg["empresa_id"],
            "empresa_id": cfg["empresa_id"],
            "project_code": cfg["project_ventas"],
            "module_code": cfg["module_ventas"],
        }

    def _inventory_context(self, context: dict, cfg: dict) -> dict:
        return {
            **context,
            "schema": cfg["schema_inventario"],
            "company_id": cfg["empresa_id"],
            "empresa_id": cfg["empresa_id"],
            "project_code": cfg["project_inv"],
            "module_code": cfg["module_inv"],
        }

    def _get_or_create_customer(self, context: dict, cfg: dict) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_ventas" / "erp_ventas_customer_get_or_create" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_ventas_customer_get_or_create_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_ventas_customer_get_or_create"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpVentasCustomerGetOrCreateService().ejecutar(self._inventory_context(context, cfg))

    def _get_product(self, context: dict, cfg: dict, product_id: str) -> dict:
        result = SupabaseClient(self._inventory_context(context, cfg)).rest_select(
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
                    "lot_code": str(item.get("lot_code") or "").strip() or None,
                }
            )
        return parsed, None

    def _enrich_cost_snapshots(self, context: dict, cfg: dict, items: list[dict], dry_run: bool) -> tuple[list[dict], str | None]:
        enriched = []
        for idx, item in enumerate(items, start=1):
            product_id = item.get("product_id")
            if not product_id:
                enriched.append(item)
                continue
            costing_result = self._sale_cost_snapshot(context, cfg, product_id, item.get("quantity"), item.get("lot_code"))
            if not costing_result.get("ok"):
                return [], f"item {idx}: {costing_result.get('error')}"
            data = costing_result.get("data") or {}
            item = {
                **item,
                "lot_code": data.get("lot_code") or None,
                "lot_cost_snapshot": round(float(data.get("lot_unit_cost") or 0), 4),
                "avg_cost_snapshot": round(float(data.get("weighted_avg_cost_after_sale") or data.get("weighted_avg_cost") or 0), 4),
                "weighted_avg_cost_snapshot": round(float(data.get("weighted_avg_cost") or 0), 4),
                "last_cost_snapshot": round(float(data.get("last_purchase_cost") or 0), 4),
            }
            enriched.append(item)
        return enriched, None

    def _sale_cost_snapshot(self, context: dict, cfg: dict, product_id: str, quantity: float, lot_code: str | None) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_costing" / "erp_costing_sale_snapshot" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_costing_sale_snapshot_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_costing_sale_snapshot"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpCostingSaleSnapshotService().ejecutar({**self._inventory_context(context, cfg), "product_id": product_id, "quantity": quantity, "lot_code": lot_code})

    def _reserve_folio(self, context: dict, table: str, prefix: str, digits: int = 5) -> dict:
        result = SupabaseClient(context).rest_select(
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
        cfg_result = self._cfg(context)
        if not cfg_result.get("ok"):
            return cfg_result
        cfg = cfg_result["data"]
        max_num = 0
        sources = [
            (
                SupabaseClient(self._sales_context(context, cfg)).rest_select(
                    "sales_documents",
                    filters={"folio": "ilike.REM-%"},
                    select="folio",
                    limit=10000,
                ),
                "folio",
            ),
            (
                SupabaseClient(self._inventory_context(context, cfg)).rest_select(
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
        cfg: dict,
        item: dict,
        remision_folio: str,
        doc_id: str,
        item_id: str | None,
        item_folio: str,
        customer_id: str,
        customer_name: str,
        delivery_address: str | None,
        movement_date: str,
        notes: str | None = None,
        paid_amount: float = 0,
    ) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_inventory" / "erp_inventory_kardex_save" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_kardex_save_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_kardex_save"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryKardexSaveService().ejecutar(
            {
                **self._inventory_context(context, cfg),
                "dry_run": False,
                "allow_custom_folio": True,
                "product_id": item["product_id"],
                "product_name_snapshot": item["description"],
                "lot_code": item.get("lot_code"),
                "source_type": "remision",
                "source_folio": remision_folio,
                "quantity": item["quantity"],
                "unit_cost": item.get("lot_cost_snapshot"),
                "total_cost": round(float(item.get("lot_cost_snapshot") or 0) * float(item["quantity"] or 0), 4),
                "unit_price": item["unit_price"],
                "total_sale": item["line_total"],
                "movement_date": movement_date,
                "party_id": customer_id,
                "party_name_snapshot": customer_name,
                "delivery_address": delivery_address,
                "notes": notes,
                "paid_amount": paid_amount,
                "metadata": {
                    "sales_schema": cfg["schema_ventas"],
                    "remision_id": doc_id,
                    "remision_folio": remision_folio,
                    "remision_item_id": item_id,
                    "remision_item_folio": item_folio,
                    "lot_code": item.get("lot_code"),
                    "line_subtotal": item.get("line_subtotal"),
                    "tax_rate": item.get("tax_rate"),
                    "tax_amount": item.get("tax_amount"),
                    "line_total": item.get("line_total"),
                    "lot_unit_cost": item.get("lot_cost_snapshot"),
                    "last_purchase_cost": item.get("last_cost_snapshot"),
                    "weighted_avg_cost": item.get("weighted_avg_cost_snapshot"),
                    "weighted_avg_cost_after_sale": item.get("avg_cost_snapshot"),
                    "lot_cost_snapshot": item.get("lot_cost_snapshot"),
                    "avg_cost_snapshot": item.get("avg_cost_snapshot"),
                    "last_cost_snapshot": item.get("last_cost_snapshot"),
                },
            }
        )

    def _log_event(self, ctx: dict, cfg: dict, doc_id: str, doc_folio: str, customer_id: str, total: float) -> dict:
        folio_num = re.sub(r"[^0-9]", "", doc_folio) or "0"
        return SupabaseClient(ctx).rest_insert(
            "sales_events",
            {
                "folio": f"EVT-REM-{folio_num}",
                "empresa_id": cfg["empresa_id"],
                "project_code": cfg["project_ventas"],
                "module_code": cfg["module_ventas"],
                "event_type": "remision_created",
                "document_id": doc_id,
                "customer_id": customer_id,
                "payload": {"folio": doc_folio, "total": total},
            },
        )
