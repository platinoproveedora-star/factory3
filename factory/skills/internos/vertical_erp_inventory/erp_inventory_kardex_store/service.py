from __future__ import annotations


class ErpInventoryKardexStoreService:
    def ejecutar(self, context: dict) -> dict:
        movement_type = str(context.get("movement_type") or "").strip()
        quantity_in = float(context.get("quantity_in") or 0)
        quantity_out = float(context.get("quantity_out") or 0)
        current_stock = float(context.get("current_stock") or 0)
        balance_after = context.get("balance_after")
        if balance_after is None:
            balance_after = current_stock + quantity_in - quantity_out
        unit_cost = self._num(context.get("unit_cost"))
        unit_price = self._num(context.get("unit_price"))
        total_cost = self._num(context.get("total_cost"), quantity_in * unit_cost)
        total_sale = self._num(context.get("total_sale"), quantity_out * unit_price)
        paid_amount = self._num(context.get("paid_amount"))
        base_amount = total_sale if movement_type == "salida" else total_cost
        balance_amount = self._num(context.get("balance_amount"), max(base_amount - paid_amount, 0))
        identity = self._identity(context)
        if not identity.get("ok"):
            return identity
        row = {
            "folio": context.get("folio"),
            "empresa_id": identity["data"]["empresa_id"],
            "project_code": identity["data"]["project_code"],
            "module_code": identity["data"]["module_code"],
            "movement_type": movement_type,
            "source_type": context.get("source_type"),
            "source_folio": context.get("source_folio"),
            "external_folio": context.get("external_folio"),
            "purchase_folio": context.get("purchase_folio"),
            "remission_folio": context.get("remission_folio"),
            "quote_folio": context.get("quote_folio"),
            "order_folio": context.get("order_folio"),
            "invoice_folio": context.get("invoice_folio"),
            "product_id": context.get("product_id"),
            "product_name_snapshot": context.get("product_name_snapshot"),
            "customer_id": context.get("customer_id"),
            "customer_name_snapshot": context.get("customer_name_snapshot"),
            "supplier_id": context.get("supplier_id"),
            "supplier_name_snapshot": context.get("supplier_name_snapshot"),
            "movement_date": context.get("movement_date"),
            "quantity_in": quantity_in,
            "quantity_out": quantity_out,
            "balance_after": float(balance_after),
            "unit_cost": unit_cost,
            "unit_price": unit_price,
            "total_cost": total_cost,
            "total_sale": total_sale,
            "payment_status": context.get("payment_status") or "pendiente",
            "paid_amount": paid_amount,
            "balance_amount": balance_amount,
            "notes": context.get("notes"),
            "created_by_user_id": context.get("created_by_user_id"),
            "erp_tags": context.get("erp_tags") or {},
            "metadata": context.get("metadata") or {},
        }
        return {"ok": True, "data": {"dry_run": context.get("dry_run", True), "movement": row}}

    def _num(self, value, default: float = 0.0) -> float:
        if value is None:
            return float(default)
        return float(value)

    def _identity(self, context: dict) -> dict:
        data = {
            "empresa_id": str(context.get("empresa_id") or context.get("company_id") or "").strip(),
            "project_code": str(context.get("project_code") or "").strip(),
            "module_code": str(context.get("module_code") or "").strip(),
        }
        missing = [key for key, value in data.items() if not value]
        if missing:
            return {"ok": False, "error": f"identidad ERP incompleta: {', '.join(missing)}"}
        return {"ok": True, "data": data}
