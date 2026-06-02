from __future__ import annotations

import importlib.util
import re
from datetime import date
from pathlib import Path

from factory.engine import SupabaseClient

_SKILLS_ROOT = Path(__file__).resolve().parents[3]


class ErpVentasRemisionCreateService:
    def ejecutar(self, context: dict) -> dict:
        customer_id = str(context.get("customer_id") or "").strip()
        items       = context.get("items") or []
        dry_run     = context.get("dry_run", True)

        if not customer_id:
            return {"ok": False, "error": "customer_id requerido"}
        if not items or not isinstance(items, list):
            return {"ok": False, "error": "items requerido (lista con al menos 1 producto)"}

        # 1. Validar y obtener snapshot del cliente desde PROY-004
        customer = self._get_customer(context, customer_id)
        if not customer:
            return {"ok": False, "error": f"cliente no encontrado en erp_parties: {customer_id}"}

        customer_name_snapshot  = str(customer.get("party_name") or "")
        customer_folio_snapshot = str(customer.get("folio") or "")

        # 2. Validar y calcular items
        parsed_items, error = self._parse_items(items)
        if error:
            return {"ok": False, "error": error}

        subtotal     = sum(i["line_total"] for i in parsed_items)
        tax_total    = sum(i["tax_amount"] for i in parsed_items)
        total        = round(subtotal + tax_total, 2)
        subtotal     = round(subtotal, 2)
        doc_date     = str(context.get("document_date") or date.today().isoformat())
        external_folio = str(context.get("external_folio") or "").strip() or None
        notes        = str(context.get("notes") or "").strip() or None

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se guardo remision",
                "data": {
                    "folio": "REM-DRYRUN",
                    "customer_name_snapshot": customer_name_snapshot,
                    "subtotal": subtotal,
                    "total": total,
                    "items_count": len(parsed_items),
                },
            }

        # 3. Reservar folio REM-XXXXX
        folio_result = self._reserve_folio(context, "sales_documents", "REM")
        if not folio_result.get("ok"):
            return folio_result
        doc_folio = folio_result["data"]["folio"]

        # 4. Insertar documento
        ctx_ventas = {**context, "schema": "uc101_proy002"}
        doc_row = {
            "folio":                  doc_folio,
            "empresa_id":             "EMP_DURALON",
            "project_code":           "PROY-002",
            "module_code":            "ventas",
            "document_type":          "remision",
            "external_folio":         external_folio,
            "customer_id":            customer_id,
            "customer_name_snapshot": customer_name_snapshot,
            "customer_folio_snapshot": customer_folio_snapshot,
            "status":                 "emitida",
            "document_date":          doc_date,
            "currency":               "MXN",
            "subtotal":               subtotal,
            "discount_total":         0,
            "tax_total":              tax_total,
            "total":                  total,
            "paid_total":             0,
            "balance_total":          total,
            "notes":                  notes,
        }
        doc_result = SupabaseClient(ctx_ventas).rest_insert("sales_documents", doc_row)
        if not doc_result.get("ok"):
            return {"ok": False, "error": f"error al crear documento: {doc_result.get('error')}"}

        doc_data = (doc_result.get("data") or [{}])
        doc_id   = (doc_data[0] if isinstance(doc_data, list) else doc_data).get("id")

        # 5. Insertar items
        kardex_errors = []
        items_saved   = []
        for i, item in enumerate(parsed_items, start=1):
            item_folio_result = self._reserve_folio(context, "sales_document_items", "REMI")
            if not item_folio_result.get("ok"):
                return item_folio_result
            item_folio = item_folio_result["data"]["folio"]

            item_row = {
                "folio":           item_folio,
                "empresa_id":      "EMP_DURALON",
                "project_code":    "PROY-002",
                "module_code":     "ventas",
                "document_id":     doc_id,
                "product_id":      item.get("product_id"),
                "description":     item["description"],
                "quantity":        item["quantity"],
                "unit":            item["unit"],
                "unit_price":      item["unit_price"],
                "discount_amount": 0,
                "tax_rate":        item["tax_rate"],
                "tax_amount":      item["tax_amount"],
                "line_total":      item["line_total"],
            }
            SupabaseClient(ctx_ventas).rest_insert("sales_document_items", item_row)
            items_saved.append(item_folio)

            # 6. Descontar inventario en PROY-004 si hay product_id
            if item.get("product_id"):
                k_result = self._kardex_salida(context, item, doc_folio)
                if not k_result.get("ok"):
                    kardex_errors.append(f"{item['description']}: {k_result.get('error')}")

        # 7. Registrar evento
        self._log_event(ctx_ventas, doc_id, doc_folio, customer_id, total)

        return {
            "ok": True,
            "data": {
                "folio":                  doc_folio,
                "document_id":            doc_id,
                "customer_name_snapshot": customer_name_snapshot,
                "subtotal":               subtotal,
                "tax_total":              tax_total,
                "total":                  total,
                "items":                  items_saved,
                "kardex_errors":          kardex_errors,
            },
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    def _get_customer(self, context: dict, customer_id: str) -> dict | None:
        ctx = {**context, "schema": "uc101_proy004"}
        result = SupabaseClient(ctx).rest_select(
            "erp_parties",
            filters={"id": f"eq.{customer_id}", "active": "eq.true"},
            select="id,folio,party_name,phone,email",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _parse_items(self, items: list) -> tuple[list, str | None]:
        parsed = []
        for idx, item in enumerate(items):
            desc = str(item.get("description") or item.get("product_name") or "").strip()
            if not desc:
                return [], f"item {idx+1}: description requerido"
            try:
                qty   = float(item.get("quantity") or 1)
                price = float(item.get("unit_price") or 0)
            except (ValueError, TypeError):
                return [], f"item {idx+1}: quantity y unit_price deben ser numericos"
            if qty <= 0:
                return [], f"item {idx+1}: quantity debe ser mayor a 0"
            if price < 0:
                return [], f"item {idx+1}: unit_price no puede ser negativo"
            tax_rate   = float(item.get("tax_rate") or 0)
            line_sub   = round(qty * price, 4)
            tax_amount = round(line_sub * tax_rate, 4)
            line_total = round(line_sub + tax_amount, 4)
            parsed.append({
                "product_id":  item.get("product_id"),
                "description": desc,
                "quantity":    qty,
                "unit":        str(item.get("unit") or "pieza"),
                "unit_price":  price,
                "tax_rate":    tax_rate,
                "tax_amount":  tax_amount,
                "line_total":  line_total,
            })
        return parsed, None

    def _reserve_folio(self, context: dict, table: str, prefix: str) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp" / "erp_folio_reserve" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_folio_reserve_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_folio_reserve"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpFolioReserveService().ejecutar({
            **context,
            "dry_run":      False,
            "schema":       "uc101_proy002",
            "project_code": "PROY-002",
            "module_code":  "ventas",
            "empresa_id":   "EMP_DURALON",
            "table":        table,
            "scope":        table,
            "prefix":       prefix,
            "folio_column": "folio",
            "digits":       5,
        })

    def _kardex_salida(self, context: dict, item: dict, remision_folio: str) -> dict:
        service_path = _SKILLS_ROOT / "vertical_erp_inventory" / "erp_inventory_kardex_save" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_kardex_save_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_kardex_save"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryKardexSaveService().ejecutar({
            **context,
            "dry_run":         False,
            "product_id":      item["product_id"],
            "movement_type":   "salida",
            "source_type":     "remision",
            "quantity":        item["quantity"],
            "unit_cost":       item.get("unit_price"),
            "remission_folio": remision_folio,
            "notes":           f"Remision {remision_folio} — {item['description']}",
        })

    def _log_event(self, ctx: dict, doc_id: str, doc_folio: str, customer_id: str, total: float) -> None:
        folio_num = re.sub(r"[^0-9]", "", doc_folio) or "0"
        event_folio = f"EVT-REM-{folio_num}"
        SupabaseClient(ctx).rest_insert("sales_events", {
            "folio":        event_folio,
            "empresa_id":   "EMP_DURALON",
            "project_code": "PROY-002",
            "module_code":  "ventas",
            "event_type":   "remision_created",
            "document_id":  doc_id,
            "customer_id":  customer_id,
            "payload":      {"folio": doc_folio, "total": total},
        })
