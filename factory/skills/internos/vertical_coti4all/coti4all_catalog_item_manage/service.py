from __future__ import annotations
import re
from factory.engine import SupabaseClient

_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


class Coti4AllCatalogItemManageService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._tenant_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]

        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        sku = str(context.get("sku") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}
        if not sku:
            return {"ok": False, "error": "sku_requerido"}

        values: dict = {}
        if "nombre" in context or "product_name" in context:
            values["nombre"] = str(context.get("nombre") or context.get("product_name") or "").strip()
        if "costo_referencia" in context or "costo" in context:
            costo = self._to_amount(context.get("costo_referencia") if "costo_referencia" in context else context.get("costo"))
            if costo is None or costo < 0:
                return {"ok": False, "error": "invalid_costo"}
            values["costo_referencia"] = costo
        if "unidad" in context:
            values["unidad"] = str(context.get("unidad") or "").strip() or None
        if "categoria" in context:
            values["categoria"] = str(context.get("categoria") or "").strip() or None
        if not values:
            return {"ok": False, "error": "sin_campos_para_actualizar"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se escribio en catalog_items", "data": {"empresa_id": empresa_id, "sku": sku, **values}}

        db = SupabaseClient(ctx)
        existing = db.rest_select(
            "catalog_items",
            filters={"empresa_id": f"eq.{empresa_id}", "sku": f"eq.{sku}"},
            select="id",
            limit=1,
        )
        if not existing.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": existing.get("error")}}

        if existing.get("data"):
            res = db.rest_update("catalog_items", values, {"empresa_id": f"eq.{empresa_id}", "sku": f"eq.{sku}"})
        else:
            row = {
                "folio": f"CAT-{empresa_id}-{sku}",
                "empresa_id": empresa_id,
                "sku": sku,
                "nombre": values.get("nombre") or sku,
                "costo_referencia": values.get("costo_referencia", 0),
                "unidad": values.get("unidad") or "pza",
                "categoria": values.get("categoria"),
                "activo": True,
            }
            res = db.rest_insert("catalog_items", row)

        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"item": (res.get("data") or [{}])[0], "warnings": []}}

    def _tenant_context(self, context: dict) -> dict:
        schema = str(context.get("schema") or context.get("company_schema") or "").strip()
        if not schema or not _VALID_SCHEMA.match(schema):
            return {"ok": False, "error": "schema requerida y valida (ej: coti4all)"}
        context["schema"] = schema
        return {"ok": True, "data": context}

    def _to_amount(self, value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
