from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import (  # noqa: E402
    SupabaseClient,
    blank,
    customer_key,
    identity_row,
    normalize_date,
    reserve_folio,
    resolve_followup_context,
    utc_now,
)


class ErpClientFollowupUpsertService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_followup_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        name = blank(context.get("customer_name"))
        key = customer_key(context.get("customer_key") or name)
        if not key:
            return {"ok": False, "error": "customer_key o customer_name requerido"}
        if not name:
            name = key

        try:
            last_call_date = normalize_date(context.get("last_call_date"), "last_call_date")
            next_followup_date = normalize_date(context.get("next_followup_date"), "next_followup_date")
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        payload = {
            "customer_id": blank(context.get("customer_id")),
            "customer_key": key,
            "customer_name": name,
            "comments": blank(context.get("comments")),
            "last_call_date": last_call_date,
            "next_followup_date": next_followup_date,
            "offer_prices": blank(context.get("offer_prices")),
            "status": blank(context.get("status")) or "activo",
            "updated_at": utc_now(),
        }
        dry_run = bool(context.get("dry_run", True))
        filters = {
            **identity_row(ctx),
            "customer_key": key,
        }

        db = SupabaseClient(ctx)
        if not dry_run and not context.get("skip_schema_ensure"):
            ensured = self._ensure_table(ctx)
            if not ensured.get("ok"):
                return ensured
        existing_result = db.rest_select(
            "erp_client_followups",
            filters=filters,
            select="id,folio",
            limit=1,
        )
        if not existing_result.get("ok"):
            return existing_result
        existing = (existing_result.get("data") or [None])[0]

        if dry_run:
            return {
                "ok": True,
                "message": "dry_run: no se guardo seguimiento de cliente",
                "data": {"mode": "update" if existing else "insert", "row": {**filters, **payload}},
            }

        if existing:
            result = db.rest_update("erp_client_followups", payload, {"id": existing["id"]})
        else:
            folio_result = reserve_folio(ctx, "erp_client_followups", "ECF")
            if not folio_result.get("ok"):
                return folio_result
            result = db.rest_insert(
                "erp_client_followups",
                {
                    "folio": folio_result["data"]["folio"],
                    **filters,
                    **payload,
                },
            )
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        return {
            "ok": True,
            "data": {
                "mode": "update" if existing else "insert",
                "followup": rows[0] if rows else {**filters, **payload},
            },
        }

    def _ensure_table(self, context: dict) -> dict:
        service_path = Path(__file__).resolve().parents[1] / "erp_client_followup_schema_plan" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_client_followup_schema_plan_service", service_path)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar erp_client_followup_schema_plan"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plan = module.ErpClientFollowupSchemaPlanService().ejecutar(context)
        if not plan.get("ok"):
            return plan
        sql = (plan.get("data") or {}).get("sql")
        if not sql:
            return {"ok": False, "error": "schema_plan no devolvio SQL"}
        result = SupabaseClient(context).management_query(sql)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"ensured": True}}
