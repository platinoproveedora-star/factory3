from __future__ import annotations

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


class InventoryValuationListService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        filters = {"company_id": f"eq.{company_id}"}
        if context.get("environment"):
            filters["environment"] = f"eq.{str(context['environment']).strip().lower()}"

        res = db.rest_select("inventory_period_balance", filters=filters, select="*", order="year.desc,month.desc", limit=5000)
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}

        latest: dict[tuple, dict] = {}
        for row in res.get("data") or []:
            key = (row["product_id"], row.get("warehouse_id"), row["environment"])
            if key not in latest:
                latest[key] = row

        rows = list(latest.values())
        product_ids = list({row["product_id"] for row in rows})
        warehouse_ids = list({row["warehouse_id"] for row in rows if row.get("warehouse_id")})

        products_by_id = {}
        if product_ids:
            p_res = db.rest_select("products", filters={"id": f"in.({','.join(product_ids)})"}, select="id,fiscal_product_name,source_product_key")
            if p_res.get("ok"):
                products_by_id = {p["id"]: p for p in p_res.get("data") or []}

        warehouses_by_id = {}
        if warehouse_ids:
            w_res = db.rest_select("warehouses", filters={"id": f"in.({','.join(warehouse_ids)})"}, select="id,code,name")
            if w_res.get("ok"):
                warehouses_by_id = {w["id"]: w for w in w_res.get("data") or []}

        total_value = 0.0
        valuation = []
        for row in rows:
            product = products_by_id.get(row["product_id"], {})
            warehouse = warehouses_by_id.get(row.get("warehouse_id"), {})
            closing_value = float(row.get("closing_value") or 0)
            total_value += closing_value
            valuation.append({
                "product_id": row["product_id"],
                "fiscal_product_name": product.get("fiscal_product_name"),
                "source_product_key": product.get("source_product_key"),
                "warehouse_code": warehouse.get("code"),
                "environment": row["environment"],
                "year": row["year"],
                "month": row["month"],
                "closing_qty": row.get("closing_qty"),
                "closing_value": closing_value,
            })

        return {"ok": True, "data": {"valuation": valuation, "total_value": round(total_value, 2)}}
