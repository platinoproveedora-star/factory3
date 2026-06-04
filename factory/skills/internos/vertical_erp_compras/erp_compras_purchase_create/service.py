from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

from factory.engine import SupabaseClient


class ErpComprasPurchaseCreateService:
    def ejecutar(self, context: dict) -> dict:
        ctx = {
            **context,
            "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004",
            "company_id": context.get("company_id") or "EMP_DURALON",
            "project_code": context.get("project_code") or "PROY-004",
            "module_code": "compras",
        }
        supplier_id = str(context.get("supplier_id") or context.get("party_id") or "").strip()
        if not supplier_id:
            return {"ok": False, "error": "supplier_id requerido"}
        items = context.get("items")
        if not isinstance(items, list) or not items:
            return {"ok": False, "error": "items requerido"}

        supplier = self._get_supplier(ctx, supplier_id)
        if not supplier.get("ok"):
            return supplier
        products = self._products(ctx)
        if not products.get("ok"):
            return products
        product_map = {str(row.get("id")): row for row in products.get("data", {}).get("products", [])}

        clean_items = []
        total_cost = 0.0
        for index, item in enumerate(items, start=1):
            product_id = str((item or {}).get("product_id") or "").strip()
            product = product_map.get(product_id)
            if not product:
                return {"ok": False, "error": f"producto invalido en renglon {index}"}
            quantity = float((item or {}).get("quantity") or 0)
            unit_cost = float((item or {}).get("unit_cost") or 0)
            if quantity <= 0:
                return {"ok": False, "error": f"cantidad invalida en renglon {index}"}
            if unit_cost < 0:
                return {"ok": False, "error": f"costo invalido en renglon {index}"}
            tax_rate = float((item or {}).get("tax_rate") or 0)
            if tax_rate not in {0.0, 0.08, 0.16, 8.0, 16.0}:
                return {"ok": False, "error": f"iva invalido en renglon {index}"}
            if tax_rate in {8.0, 16.0}:
                tax_rate = tax_rate / 100
            lot_code = self._blank((item or {}).get("lot_code")) or self._blank(context.get("lot_code")) or "GENERAL"
            subtotal_cost = round(quantity * unit_cost, 2)
            tax_amount = round(subtotal_cost * tax_rate, 2)
            line_total = round(subtotal_cost + tax_amount, 2)
            total_cost += line_total
            clean_items.append({
                "product_id": product_id,
                "product_name_snapshot": product.get("product_name"),
                "quantity": quantity,
                "unit_cost": unit_cost,
                "lot_code": lot_code,
                "subtotal_cost": subtotal_cost,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total_cost": line_total,
                "notes": self._blank((item or {}).get("notes")),
            })

        paid_amount = float(context.get("paid_amount") or 0)
        dry_run = context.get("dry_run", True)
        source_folio = context.get("source_folio") if context.get("allow_custom_folio") and context.get("source_folio") else None
        if not dry_run and not source_folio:
            folio_result = self._reserve_folio(ctx, "erp_kardex", "COM", "source_folio", "erp_kardex_source_compra")
            if not folio_result.get("ok"):
                return folio_result
            source_folio = folio_result["data"]["folio"]
        source_folio = source_folio or "COM-DRYRUN"

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se guardo compra",
                "data": {"purchase": self._summary(source_folio, supplier["data"]["supplier"], clean_items, total_cost, paid_amount, context)},
            }

        movements = []
        paid_remaining = paid_amount
        for item in clean_items:
            line_paid = min(paid_remaining, item["total_cost"])
            paid_remaining = max(paid_remaining - line_paid, 0)
            save_result = self._kardex_save({
                **ctx,
                "dry_run": False,
                "source_type": "compra",
                "allow_custom_folio": True,
                "source_folio": source_folio,
                "external_folio": self._blank(context.get("external_folio")),
                "party_id": supplier_id,
                "party_name_snapshot": supplier["data"]["supplier"].get("party_name"),
                "product_id": item["product_id"],
                "product_name_snapshot": item["product_name_snapshot"],
                "lot_code": item["lot_code"],
                "movement_date": context.get("movement_date") or date.today().isoformat(),
                "quantity": item["quantity"],
                "unit_cost": item["unit_cost"],
                "total_cost": item["total_cost"],
                "paid_amount": line_paid,
                "notes": item["notes"] or self._blank(context.get("notes")),
                "metadata": {
                    "purchase_total": round(total_cost, 2),
                    "purchase_paid_amount": paid_amount,
                    "line_count": len(clean_items),
                    "subtotal_cost": item["subtotal_cost"],
                    "tax_rate": item["tax_rate"],
                    "tax_amount": item["tax_amount"],
                    "lot_code": item["lot_code"],
                },
            })
            if not save_result.get("ok"):
                return save_result
            movements.append(save_result["data"]["movement"])

        return {
            "ok": True,
            "data": {
                "purchase": self._summary(source_folio, supplier["data"]["supplier"], clean_items, total_cost, paid_amount, context),
                "movements": movements,
            },
        }

    def _get_supplier(self, context: dict, supplier_id: str) -> dict:
        result = SupabaseClient(context).rest_select("erp_parties", filters={"id": supplier_id}, select="*", limit=1)
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        if not rows or rows[0].get("party_type") not in {"supplier", "both"}:
            return {"ok": False, "error": "proveedor no encontrado"}
        return {"ok": True, "data": {"supplier": rows[0]}}

    def _products(self, context: dict) -> dict:
        result = SupabaseClient(context).rest_select("erp_products", filters={"active": "eq.true"}, select="*", order="product_name.asc", limit=1000)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"products": result.get("data") or []}}

    def _summary(self, source_folio: str, supplier: dict, items: list[dict], total_cost: float, paid_amount: float, context: dict) -> dict:
        return {
            "source_folio": source_folio,
            "external_folio": self._blank(context.get("external_folio")),
            "supplier_id": supplier.get("id"),
            "supplier_name_snapshot": supplier.get("party_name"),
            "movement_date": context.get("movement_date") or date.today().isoformat(),
            "items": items,
            "line_count": len(items),
            "total_cost": round(total_cost, 2),
            "paid_amount": round(paid_amount, 2),
            "balance_amount": round(max(total_cost - paid_amount, 0), 2),
            "payment_status": "pagado" if total_cost and paid_amount >= total_cost else "parcial" if paid_amount > 0 else "pendiente",
            "notes": self._blank(context.get("notes")),
        }

    def _reserve_folio(self, context: dict, table: str, prefix: str, folio_column: str, scope: str) -> dict:
        service_path = Path(__file__).resolve().parents[2] / "vertical_erp" / "erp_folio_reserve" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_folio_reserve_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_folio_reserve"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpFolioReserveService().ejecutar({**context, "dry_run": False, "table": table, "scope": scope, "prefix": prefix, "folio_column": folio_column, "digits": 5})

    def _kardex_save(self, context: dict) -> dict:
        service_path = Path(__file__).resolve().parents[1] / "vertical_erp_inventory" / "erp_inventory_kardex_save" / "service.py"
        if not service_path.exists():
            service_path = Path(__file__).resolve().parents[2] / "vertical_erp_inventory" / "erp_inventory_kardex_save" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_inventory_kardex_save_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_inventory_kardex_save"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpInventoryKardexSaveService().ejecutar(context)

    def _blank(self, value):
        value = str(value or "").strip()
        return value or None
