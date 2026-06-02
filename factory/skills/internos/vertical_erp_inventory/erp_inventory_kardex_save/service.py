from __future__ import annotations

from factory.engine import SupabaseClient


class ErpInventoryKardexSaveService:
    def ejecutar(self, context: dict) -> dict:
        schema_context = {**context, "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004"}
        source_type = str(context.get("source_type") or "").strip()
        if source_type not in {"compra", "remision", "ajuste"}:
            return {"ok": False, "error": "source_type invalido"}
        if not context.get("product_id"):
            return {"ok": False, "error": "product_id requerido"}

        quantity = float(context.get("quantity") or 0)
        if quantity <= 0:
            return {"ok": False, "error": "quantity debe ser mayor a cero"}

        dry_run = context.get("dry_run", True)
        is_sale = source_type == "remision"
        is_adjustment = source_type == "ajuste"
        adjustment_direction = "salida" if context.get("adjustment_direction") == "salida" else "entrada"
        if source_type == "compra" and not context.get("party_id"):
            return {"ok": False, "error": "compra requiere proveedor"}
        if source_type == "remision" and not context.get("party_id"):
            return {"ok": False, "error": "venta requiere cliente"}

        unit_cost = float(context.get("unit_cost") or 0)
        unit_price = float(context.get("unit_price") or 0)
        total_cost = 0 if is_sale or is_adjustment else float(context.get("total_cost") or unit_cost * quantity)
        total_sale = float(context.get("total_sale") or unit_price * quantity) if is_sale else 0
        paid = float(context.get("paid_amount") or 0)
        base_amount = total_sale if is_sale else total_cost
        movement_type = "ajuste" if is_adjustment else "salida" if is_sale else "entrada"
        quantity_in = 0 if is_sale or (is_adjustment and adjustment_direction == "salida") else quantity
        quantity_out = quantity if is_sale or (is_adjustment and adjustment_direction == "salida") else 0
        source_prefix = "REM" if is_sale else "AJU" if is_adjustment else "COM"
        current_stock = self._current_stock(schema_context, context.get("product_id")) if not dry_run else 0
        balance_after = current_stock + quantity_in - quantity_out

        row = {
            "folio": context.get("folio") or ("KAR-DRYRUN" if dry_run else self._next_folio(schema_context, "erp_kardex", "KAR")),
            "movement_type": movement_type,
            "source_type": source_type,
            "source_folio": context.get("source_folio") or (f"{source_prefix}-DRYRUN" if dry_run else self._next_folio(schema_context, "erp_kardex", source_prefix)),
            "external_folio": self._blank(context.get("external_folio")),
            "purchase_folio": None if is_sale or is_adjustment else context.get("source_folio"),
            "remission_folio": context.get("source_folio") if is_sale else None,
            "product_id": context.get("product_id"),
            "product_name_snapshot": self._blank(context.get("product_name_snapshot")),
            "customer_id": context.get("party_id") if is_sale else None,
            "customer_name_snapshot": self._blank(context.get("party_name_snapshot")) if is_sale else None,
            "supplier_id": context.get("party_id") if source_type == "compra" else None,
            "supplier_name_snapshot": self._blank(context.get("party_name_snapshot")) if source_type == "compra" else None,
            "movement_date": context.get("movement_date"),
            "quantity_in": quantity_in,
            "quantity_out": quantity_out,
            "balance_after": balance_after,
            "unit_cost": None if is_sale or is_adjustment else unit_cost,
            "unit_price": unit_price if is_sale else None,
            "total_cost": total_cost,
            "total_sale": total_sale,
            "paid_amount": paid,
            "balance_amount": max(base_amount - paid, 0),
            "payment_status": context.get("payment_status") or ("pagado" if base_amount and paid >= base_amount else "parcial" if paid > 0 else "pendiente"),
            "notes": self._blank(context.get("notes")),
        }
        if dry_run:
            return {"ok": True, "message": "dry_run: no se guardo movimiento", "data": {"movement": row}}
        result = SupabaseClient(schema_context).rest_insert("erp_kardex", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        movement = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"movement": movement}}

    def _next_folio(self, context: dict, table: str, prefix: str) -> str:
        result = SupabaseClient(context).rest_select(table, filters={"folio": f"ilike.{prefix}-%"}, select="folio", limit=100, order="folio.desc")
        numbers = []
        if result.get("ok"):
            for row in result.get("data") or []:
                text = str(row.get("folio") or "")
                if text.startswith(f"{prefix}-") and text.split("-", 1)[1].isdigit():
                    numbers.append(int(text.split("-", 1)[1]))
        return f"{prefix}-{max(numbers or [0]) + 1:05d}"

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None

    def _current_stock(self, context: dict, product_id: str) -> float:
        result = SupabaseClient(context).rest_select(
            "erp_kardex",
            filters={"product_id": product_id},
            select="quantity_in,quantity_out",
            limit=1000,
        )
        if not result.get("ok"):
            return 0.0
        total = 0.0
        for row in result.get("data") or []:
            total += float(row.get("quantity_in") or 0) - float(row.get("quantity_out") or 0)
        return total
