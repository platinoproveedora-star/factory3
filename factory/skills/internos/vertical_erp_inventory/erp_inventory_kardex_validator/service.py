from __future__ import annotations


class ErpInventoryKardexValidatorService:
    def ejecutar(self, context: dict) -> dict:
        issues = []
        warnings = []
        movement_type = str(context.get("movement_type") or "").strip()
        source_type = str(context.get("source_type") or "").strip()
        quantity_in = float(context.get("quantity_in") or 0)
        quantity_out = float(context.get("quantity_out") or 0)
        current_stock = float(context.get("current_stock") or 0)

        if movement_type not in {"entrada", "salida", "ajuste", "devolucion"}:
            issues.append("movement_type invalido")
        if source_type not in {"compra", "remision", "ajuste", "devolucion"}:
            issues.append("source_type invalido")
        if not context.get("product_id"):
            issues.append("product_id requerido")
        if movement_type == "entrada" and quantity_in <= 0:
            issues.append("entrada requiere quantity_in > 0")
        if movement_type == "salida" and quantity_out <= 0:
            issues.append("salida requiere quantity_out > 0")
        if movement_type == "salida" and quantity_out > current_stock:
            issues.append("salida mayor a existencia actual")
        if source_type == "remision" and not context.get("customer_id"):
            issues.append("remision requiere customer_id")
        if source_type == "compra" and not context.get("supplier_id"):
            issues.append("compra requiere supplier_id")
        if context.get("payment_status") not in (None, "pendiente", "parcial", "pagado"):
            warnings.append("payment_status no estandar")

        return {"ok": not issues, "data": {"valid": not issues, "issues": issues, "warnings": warnings}}

