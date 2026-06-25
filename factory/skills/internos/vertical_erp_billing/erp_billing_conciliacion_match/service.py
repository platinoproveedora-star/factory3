from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, money, reserve_folio, resolve_billing_context, utc_now  # noqa: E402

_ENSURE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {schema}.billing_conciliacion_matches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL,
  empresa_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL DEFAULT 'billing',
  movement_id uuid NOT NULL,
  movement_folio text,
  payment_id uuid,
  payment_folio text,
  match_type text NOT NULL DEFAULT 'manual',
  amount_matched numeric(14,2),
  notes text,
  status text NOT NULL DEFAULT 'activo',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz
);
CREATE INDEX IF NOT EXISTS idx_billing_conc_matches_movement ON {schema}.billing_conciliacion_matches(movement_id);
CREATE INDEX IF NOT EXISTS idx_billing_conc_matches_payment ON {schema}.billing_conciliacion_matches(payment_id);
CREATE INDEX IF NOT EXISTS idx_billing_conc_matches_status ON {schema}.billing_conciliacion_matches(status);
"""

VALID_ACTIONS = {"ensure_table", "create", "cancel"}


class ErpBillingConciliacionMatchService:
    def ejecutar(self, context: dict) -> dict:
        action = blank(context.get("action")) or "create"
        if action not in VALID_ACTIONS:
            return {"ok": False, "error": f"action invalida. Opciones: {', '.join(VALID_ACTIONS)}"}

        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        if action == "ensure_table":
            return self._ensure_table(ctx)
        if action == "create":
            return self._create(ctx, context)
        return self._cancel(ctx, context)

    def _ensure_table(self, ctx: dict) -> dict:
        schema = ctx["schema"]
        sql = _ENSURE_TABLE_SQL.replace("{schema}", schema)
        db = SupabaseClient(ctx)
        result = db.management_query(sql)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"message": f"Tabla billing_conciliacion_matches lista en {schema}"}}

    def _create(self, ctx: dict, context: dict) -> dict:
        movement_id = blank(context.get("movement_id"))
        movement_folio = blank(context.get("movement_folio"))
        payment_id = blank(context.get("payment_id"))
        payment_folio = blank(context.get("payment_folio"))

        if not movement_id:
            return {"ok": False, "error": "movement_id requerido"}
        if not payment_id and not payment_folio:
            return {"ok": False, "error": "payment_id o payment_folio requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se creó el cruce", "data": {"movement_id": movement_id, "payment_id": payment_id}}

        folio_result = reserve_folio(ctx, "billing_conciliacion_matches", "CONC")
        if not folio_result.get("ok"):
            return folio_result
        folio = folio_result["data"]["folio"]

        row = {
            "folio": folio,
            "empresa_id": ctx["company_id"],
            "project_code": ctx["project_code"],
            "module_code": ctx.get("module_code") or "billing",
            "movement_id": movement_id,
            "movement_folio": movement_folio,
            "payment_id": payment_id,
            "payment_folio": payment_folio,
            "match_type": blank(context.get("match_type")) or "manual",
            "amount_matched": money(context.get("amount_matched")) or None,
            "notes": blank(context.get("notes")),
            "status": "activo",
        }

        db = SupabaseClient(ctx)
        result = db.rest_insert("billing_conciliacion_matches", [row])
        if not result.get("ok"):
            return result
        inserted = (result.get("data") or [{}])[0] if isinstance(result.get("data"), list) else result.get("data") or {}
        return {"ok": True, "data": {"match": inserted}}

    def _cancel(self, ctx: dict, context: dict) -> dict:
        match_id = blank(context.get("match_id") or context.get("id"))
        folio = blank(context.get("folio"))
        if not match_id and not folio:
            return {"ok": False, "error": "match_id o folio requerido para cancelar"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: cruce no cancelado"}

        filters = {"id": match_id} if match_id else {"folio": folio}
        db = SupabaseClient(ctx)
        result = db.rest_update("billing_conciliacion_matches", {"status": "cancelado", "updated_at": utc_now()}, filters)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"message": "cruce cancelado"}}
