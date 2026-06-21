from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _banks_common import SupabaseClient, blank, resolve_banks_context  # noqa: E402


VALID_DECISIONS = {"aprobado", "rechazado"}


class ErpBanksAuthorizationDecideService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_banks_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        movement_id = blank(context.get("movement_id"))
        decision = str(context.get("decision") or "").strip()
        decided_by = blank(context.get("decided_by"))
        default_authorizer = blank(context.get("default_authorizer"))

        if not movement_id:
            return {"ok": False, "error": "movement_id requerido"}
        if decision not in VALID_DECISIONS:
            return {"ok": False, "error": "decision invalida. Opciones: aprobado, rechazado"}
        if not decided_by:
            return {"ok": False, "error": "decided_by requerido"}
        if not default_authorizer:
            return {"ok": False, "error": "default_authorizer requerido en context"}

        params = {
            "p_movement_id": movement_id,
            "p_decision": decision,
            "p_decided_by": decided_by,
            "p_decision_notes": blank(context.get("decision_notes")),
            "p_empresa_id": ctx["company_id"],
            "p_default_authorizer": default_authorizer,
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se llamo banks_decide_authorization",
                "data": {"function_name": "banks_decide_authorization", "params": params},
            }

        result = SupabaseClient(ctx).rpc("banks_decide_authorization", params)
        if not result.get("ok"):
            return result
        return self._normalize_rpc(result)

    def _normalize_rpc(self, result: dict) -> dict:
        data = result.get("data")
        if isinstance(data, list) and data:
            data = data[0]
        if isinstance(data, dict) and "ok" in data:
            return data
        if isinstance(data, dict):
            return {"ok": True, "data": data}
        return {"ok": True, "data": {"result": data}}
