from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import db, is_dry_run, list_catalogs, now_iso, reserve_folio, resolve_context, table_filters


class LogisticsCatalogManageService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        action = str(context.get("action") or "list").strip()
        if action == "list":
            return {"ok": True, "data": list_catalogs(ctx)}
        if action == "seed_key_products":
            return self._seed_key_products(ctx, context)
        table = {"vehicle": "logistics_vehicles", "driver": "logistics_drivers", "product": "logistics_product_config"}.get(str(context.get("catalog") or ""))
        if not table:
            return {"ok": False, "error": "catalog debe ser vehicle, driver o product"}
        if action == "create":
            return self._create(ctx, context, table)
        if action == "update":
            row_id = str(context.get("id") or "").strip()
            if not row_id:
                return {"ok": False, "error": "id requerido"}
            values = {key: context[key] for key in context if key in {"nombre", "tipo", "placa", "capacidad_peso_kg", "telefono", "status", "activo", "product_key", "product_label", "priority", "active"}}
            values["updated_at"] = now_iso()
            if is_dry_run(context):
                return {"ok": True, "message": "dry_run: no se actualizo catalogo", "data": values}
            return db(ctx).rest_update(table, values, table_filters(ctx, {"id": f"eq.{row_id}"}))
        return {"ok": False, "error": "action invalida"}

    def _create(self, ctx: dict, context: dict, table: str) -> dict:
        prefix = {"logistics_vehicles": "VEH", "logistics_drivers": "CHO", "logistics_product_config": "LPC"}[table]
        folio = {"ok": True, "data": {"folio": f"{prefix}-DRYRUN"}} if is_dry_run(context) else reserve_folio(ctx, table, prefix)
        if not folio.get("ok"):
            return folio
        row = {"folio": folio["data"]["folio"], "empresa_id": ctx["company_id"], "project_code": ctx["project_code"], "module_code": ctx["module_code"]}
        if table == "logistics_vehicles":
            row.update({"nombre": context.get("nombre"), "tipo": context.get("tipo"), "placa": context.get("placa"), "capacidad_peso_kg": context.get("capacidad_peso_kg")})
        elif table == "logistics_drivers":
            row.update({"nombre": context.get("nombre"), "telefono": context.get("telefono")})
        else:
            row.update({"product_key": context.get("product_key"), "product_label": context.get("product_label"), "priority": context.get("priority") or 100})
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se creo catalogo", "data": row}
        return db(ctx).rest_insert(table, row)

    def _seed_key_products(self, ctx: dict, context: dict) -> dict:
        rows = []
        for index, product in enumerate(ctx.get("key_products") or [], start=1):
            prefix = "LPC"
            folio = {"ok": True, "data": {"folio": f"{prefix}-DRYRUN-{index}"}} if is_dry_run(context) else reserve_folio(ctx, "logistics_product_config", prefix)
            if not folio.get("ok"):
                return folio
            rows.append(
                {
                    "folio": folio["data"]["folio"],
                    "empresa_id": ctx["company_id"],
                    "project_code": ctx["project_code"],
                    "module_code": ctx["module_code"],
                    "product_key": product.get("key"),
                    "product_label": product.get("label"),
                    "priority": index,
                    "active": True,
                }
            )
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se sembraron productos", "data": {"rows": rows}}
        result = db(ctx).rest_upsert("logistics_product_config", rows, on_conflict="empresa_id,project_code,module_code,product_key")
        return result
