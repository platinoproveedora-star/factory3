from __future__ import annotations

from datetime import datetime, timezone

from factory.engine import SupabaseClient


class ErpVentasRemisionFullUpdateService:
    ALLOWED_STATUS = {"emitida", "pendiente", "pagada", "cancelada"}

    def ejecutar(self, context: dict) -> dict:
        doc_id = str(context.get("id") or context.get("document_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        items = context.get("items") or []
        if not doc_id and not folio:
            return {"ok": False, "error": "id o folio requerido"}
        if not isinstance(items, list):
            return {"ok": False, "error": "items debe ser lista"}

        ctx = {**context, "schema": "uc101_proy002"}
        doc = self._get_doc(ctx, doc_id, folio)
        if not doc:
            return {"ok": False, "error": "remision no encontrada"}
        doc_id = doc["id"]
        folio = doc["folio"]

        parsed_items, error = self._parse_items(items)
        if error:
            return {"ok": False, "error": error}

        subtotal = round(sum(i["line_subtotal"] for i in parsed_items), 2)
        tax_total = round(sum(i["tax_amount"] for i in parsed_items), 2)
        total = round(sum(i["line_total"] for i in parsed_items), 2)
        paid_total = float(doc.get("paid_total") or 0)
        status = str(context.get("status") or doc.get("status") or "emitida").strip()
        if status not in self.ALLOWED_STATUS:
            return {"ok": False, "error": "status invalido"}
        header = {
            "external_folio": self._blank(context.get("external_folio")),
            "delivery_address": self._blank(context.get("delivery_address")),
            "status": status,
            "document_date": str(context.get("document_date") or doc.get("document_date")),
            "notes": self._blank(context.get("notes")),
            "subtotal": subtotal,
            "tax_total": tax_total,
            "total": total,
            "balance_total": max(total - paid_total, 0),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo remision completa", "data": {"remision": {**doc, **header}, "items": parsed_items}}

        db = SupabaseClient(ctx)
        doc_update = db.rest_update("sales_documents", header, {"id": doc_id})
        if not doc_update.get("ok"):
            return doc_update

        saved_items = []
        for index, item in enumerate(parsed_items, start=1):
            item_id = item.get("id")
            if not item_id:
                return {"ok": False, "error": f"item {index}: id requerido para edicion"}
            product = self._get_product(context, item.get("product_id")) if item.get("product_id") else {}
            update = {
                "product_id": item.get("product_id"),
                "inventory_product_id": item.get("product_id"),
                "product_folio_snapshot": product.get("folio"),
                "product_name_snapshot": product.get("product_name") or item["description"],
                "description": item["description"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "unit_price": item["unit_price"],
                "tax_rate": item["tax_rate"],
                "tax_amount": item["tax_amount"],
                "line_total": item["line_total"],
                "updated_at": header["updated_at"],
            }
            item_res = db.rest_update("sales_document_items", update, {"id": item_id, "document_id": doc_id})
            if not item_res.get("ok"):
                return {"ok": False, "error": f"error actualizando item {index}: {item_res.get('error')}"}
            item_data = item_res.get("data") or []
            saved = item_data[0] if isinstance(item_data, list) and item_data else item_data
            saved_items.append(saved)
            self._sync_kardex(context, folio, item_id, item, product, header)

        data = doc_update.get("data") or []
        remision = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"remision": remision, "items": saved_items}}

    def _get_doc(self, context: dict, doc_id: str, folio: str) -> dict | None:
        filters = {"id": doc_id} if doc_id else {"folio": folio}
        result = SupabaseClient(context).rest_select(
            "sales_documents",
            filters=filters,
            select="id,folio,status,document_date,paid_total",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _parse_items(self, items: list) -> tuple[list, str | None]:
        parsed = []
        for idx, item in enumerate(items):
            desc = str(item.get("description") or item.get("product_name") or "").strip()
            if not desc:
                return [], f"item {idx + 1}: description requerido"
            try:
                qty = float(item.get("quantity") or 0)
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
                    "id": item.get("id"),
                    "product_id": item.get("product_id") or item.get("inventory_product_id"),
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

    def _sync_kardex(self, context: dict, remision_folio: str, item_id: str, item: dict, product: dict, header: dict) -> None:
        db = SupabaseClient({**context, "schema": "uc101_proy004"})
        result = db.rest_select(
            "erp_kardex",
            filters={"source_type": "remision", "source_folio": remision_folio},
            select="id,metadata",
            limit=500,
        )
        if not result.get("ok"):
            return
        target_id = None
        for row in result.get("data") or []:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if str(metadata.get("remision_item_id") or "") == str(item_id):
                target_id = row.get("id")
                break
        if not target_id:
            return
        db.rest_update(
            "erp_kardex",
            {
                "product_id": item.get("product_id"),
                "product_name_snapshot": product.get("product_name") or item["description"],
                "movement_date": header.get("document_date"),
                "delivery_address": header.get("delivery_address"),
                "quantity_out": item["quantity"],
                "unit_price": item["unit_price"],
                "total_sale": item["line_total"],
                "balance_amount": item["line_total"],
                "notes": f"Remision {remision_folio} - {item['description']}",
                "updated_at": header["updated_at"],
            },
            {"id": target_id},
        )

    def _get_product(self, context: dict, product_id: str) -> dict:
        result = SupabaseClient({**context, "schema": "uc101_proy004"}).rest_select(
            "erp_products",
            filters={"id": f"eq.{product_id}"},
            select="id,folio,product_name,unit,category",
            limit=1,
        )
        rows = result.get("data") or []
        return rows[0] if rows else {}

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
