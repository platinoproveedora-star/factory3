from __future__ import annotations

import importlib.util
from pathlib import Path

from factory.engine import SupabaseClient


def _common():
    path = Path(__file__).resolve().parents[1] / "_common.py"
    spec = importlib.util.spec_from_file_location("multi_shopper_common", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SupplierSearchSkillService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = _common().resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        filters = {"company_id": ctx["company_id"]}
        if ctx.get("status"):
            filters["status"] = ctx["status"]
        result = SupabaseClient(ctx).rest_select("suppliers", filters=filters, select="*", order="name.asc", limit=int(ctx.get("limit") or 1000))
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        query = str(ctx.get("q") or ctx.get("query") or "").lower().strip()
        if query:
            rows = [row for row in rows if query in " ".join(str(row.get(k) or "") for k in ("name", "legal_name", "city", "state", "supplier_type", "notes")).lower()]
        category = str(ctx.get("category_name") or ctx.get("category") or "").lower().strip()
        if category:
            cat_result = SupabaseClient(ctx).rest_select("supplier_categories", filters={"company_id": ctx["company_id"], "category_name": f"ilike.*{category}*"}, select="supplier_id", limit=1000)
            if not cat_result.get("ok"):
                return cat_result
            supplier_ids = {row.get("supplier_id") for row in cat_result.get("data") or []}
            rows = [row for row in rows if row.get("id") in supplier_ids]
        return {"ok": True, "data": {"suppliers": rows}}
