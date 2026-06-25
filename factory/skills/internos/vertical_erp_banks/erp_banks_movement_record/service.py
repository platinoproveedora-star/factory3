from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _banks_common import SupabaseClient, blank, money, resolve_banks_context, today_iso  # noqa: E402

VALID_MOVEMENT_TYPES = {"entrada", "salida"}
VALID_SOURCE_TYPES = {"pago", "transferencia", "ajuste", "corte", "apertura", "devolucion"}


class ErpBanksMovementRecordService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_banks_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        account_id = str(context.get("account_id") or "").strip()
        account_folio = str(context.get("account_folio") or "").strip()
        if not account_id and not account_folio:
            return {"ok": False, "error": "account_id o account_folio requerido"}

        movement_type = str(context.get("movement_type") or "").strip()
        source_type = str(context.get("source_type") or "").strip()
        amount = money(context.get("amount"))

        if movement_type not in VALID_MOVEMENT_TYPES:
            return {"ok": False, "error": f"movement_type invalido. Opciones: {', '.join(VALID_MOVEMENT_TYPES)}"}
        if source_type not in VALID_SOURCE_TYPES:
            return {"ok": False, "error": f"source_type invalido. Opciones: {', '.join(sorted(VALID_SOURCE_TYPES))}"}
        if amount <= 0:
            return {"ok": False, "error": "amount debe ser mayor a 0"}
        if source_type == "transferencia" and not str(context.get("transfer_group_id") or "").strip():
            return {"ok": False, "error": "transfer_group_id requerido para transferencias"}

        params = {
            "p_account_id": account_id or None,
            "p_account_folio": account_folio or None,
            "p_movement_type": movement_type,
            "p_source_type": source_type,
            "p_source_module": blank(context.get("source_module")) or "manual",
            "p_source_id": blank(context.get("source_id")),
            "p_source_folio": blank(context.get("source_folio")),
            "p_amount": amount,
            "p_movement_date": str(context.get("movement_date") or today_iso()),
            "p_transfer_group_id": blank(context.get("transfer_group_id")),
            "p_reversal_of_movement_id": blank(context.get("reversal_of_movement_id")),
            "p_clave_rastreo": blank(context.get("clave_rastreo")),
            "p_value_date": blank(context.get("value_date")),
            "p_notes": blank(context.get("notes")),
            "p_metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
            "p_empresa_id": ctx["company_id"],
            "p_project_code": ctx["project_code"],
            "p_module_code": ctx["module_code"],
            "p_requested_by": blank(context.get("requested_by")),
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se llamo banks_record_movement",
                "data": {
                    "function_name": "banks_record_movement",
                    "params": params,
                },
            }

        result = SupabaseClient(ctx).rpc("banks_record_movement", params)
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
