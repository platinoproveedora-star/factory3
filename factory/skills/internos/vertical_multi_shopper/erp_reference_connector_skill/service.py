from __future__ import annotations

from factory.engine import SupabaseClient


class ErpReferenceConnectorSkillService:
    def ejecutar(self, context: dict) -> dict:
        schema = str(context.get("erp_schema") or context.get("inventory_schema") or context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "erp_schema/inventory_schema requerido"}
        kind = str(context.get("kind") or context.get("action") or "products").strip()
        ctx = {**context, "schema": schema}
        db = SupabaseClient(ctx)
        if kind in {"products", "product_list"}:
            result = db.rest_select("erp_products", filters={"active": "eq.true"}, select="*", order="product_name.asc", limit=int(context.get("limit") or 1000))
            if not result.get("ok"):
                return result
            return {"ok": True, "data": {"products": result.get("data") or []}}
        if kind in {"suppliers", "supplier_list"}:
            result = db.rest_select("erp_parties", filters={"active": "eq.true"}, select="*", order="party_name.asc", limit=int(context.get("limit") or 1000))
            if not result.get("ok"):
                return result
            rows = [row for row in result.get("data") or [] if row.get("party_type") in {"supplier", "both"}]
            return {"ok": True, "data": {"suppliers": rows}}
        if kind in {"categories", "category_list"}:
            result = db.rest_select("erp_products", filters={"active": "eq.true"}, select="category", order="category.asc", limit=1000)
            if not result.get("ok"):
                return result
            categories = sorted({row.get("category") for row in result.get("data") or [] if row.get("category")})
            return {"ok": True, "data": {"categories": categories}}
        if kind in {"units", "unit_list"}:
            result = db.rest_select("erp_products", filters={"active": "eq.true"}, select="unit", order="unit.asc", limit=1000)
            if not result.get("ok"):
                return result
            units = sorted({row.get("unit") for row in result.get("data") or [] if row.get("unit")})
            return {"ok": True, "data": {"units": units}}
        return {"ok": False, "error": f"kind/action no soportado: {kind}"}
