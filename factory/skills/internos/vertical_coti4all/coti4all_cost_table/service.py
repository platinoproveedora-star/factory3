from __future__ import annotations
import re
from decimal import Decimal
from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


class Coti4AllCostTableService:
    def _dec(self, v, default=0):
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal(str(default))

    def _r(self, v):
        return v.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")

    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        product_id = str(context.get("product_id") or context.get("id") or context.get("product_code") or context.get("sku") or "").strip()
        line_qty = self._dec(context.get("qty") or context.get("quantity") or 1)

        if not product_id:
            return {"ok": False, "error": "product_id o product_code requerido"}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run — sin consulta Supabase",
                "data": {"schema": ctx["schema"], "product_id": product_id, "qty": float(line_qty)},
            }

        try:
            product = self._resolve_product(ctx, product_id)
            if not product:
                return {"ok": False, "error": "producto no encontrado"}

            amount = self._dec(product.get("costo_referencia") or 0)
            line_cost = self._r(amount * line_qty)
            return {
                "ok": True,
                "schema": ctx["schema"],
                "data": {
                    "product_id": product.get("id"),
                    "sku": product.get("sku"),
                    "product_name": product.get("nombre"),
                    "amount": float(amount),
                    "qty": float(line_qty),
                    "line_cost": float(line_cost),
                    "currency": "MXN",
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _tenant_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or "").strip()
        if not schema or not _VALID_SCHEMA.match(schema):
            return {"ok": False, "error": "schema requerida y valida (ej: coti4all)"}
        context["schema"] = schema
        return {"ok": True, "data": context}

    def _resolve_product(self, ctx: dict, value: str) -> dict | None:
        if re.match(r"^[0-9a-fA-F-]{36}$", value):
            filters = {"id": f"eq.{value}"}
        else:
            filters = {"sku": f"eq.{value}", "activo": "eq.true"}
        res = SupabaseClient(ctx).rest_select(
            "catalog_items", filters=filters, select="id,sku,nombre,costo_referencia", limit=1
        )
        rows = res.get("data") or []
        return rows[0] if rows else None
