from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _banks_common import SupabaseClient, blank, resolve_banks_context, utc_now  # noqa: E402


VALID_RECONCILIATION_STATUS = {"conciliado", "en_disputa", "no_aplica"}


class ErpBanksMarkReconciledService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_banks_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        movement_id = blank(context.get("movement_id"))
        status = str(context.get("reconciliation_status") or "").strip()
        if not movement_id:
            return {"ok": False, "error": "movement_id requerido"}
        if status not in VALID_RECONCILIATION_STATUS:
            return {"ok": False, "error": "reconciliation_status invalido. Opciones: conciliado, en_disputa, no_aplica"}

        values = {
            "reconciliation_status": status,
            "reconciled_at": blank(context.get("reconciled_at")) or (utc_now() if status == "conciliado" else None),
            "updated_at": utc_now(),
        }
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se actualizo conciliacion",
                "data": {"movement_id": movement_id, "values": values},
            }

        db = SupabaseClient(ctx)
        movement_result = db.rest_select(
            "banks_movements",
            filters={"id": movement_id, "empresa_id": ctx["company_id"]},
            select="id,folio,empresa_id,authorization_status,reconciliation_status",
            limit=1,
        )
        if not movement_result.get("ok"):
            return movement_result
        rows = movement_result.get("data") or []
        if not rows:
            return {"ok": False, "error": "movimiento no encontrado"}
        if str(rows[0].get("authorization_status") or "") != "autorizado":
            return {"ok": False, "error": "solo movimientos autorizados pueden conciliarse"}

        result = db.rest_update("banks_movements", values, {"id": movement_id, "empresa_id": ctx["company_id"]})
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        movement = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {"movement": movement}}
