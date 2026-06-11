from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, fetch_one, identity_row, money, reserve_folio, resolve_banks_context, today_iso  # noqa: E402

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

        db = SupabaseClient(ctx)
        filters = {"id": account_id} if account_id else {"folio": account_folio}
        account = fetch_one(db, "banks_accounts", filters, "id,folio,account_name,current_balance,status,empresa_id")
        if not account:
            return {"ok": False, "error": "cuenta no encontrada"}
        if str(account.get("empresa_id") or "") != ctx["company_id"]:
            return {"ok": False, "error": "cuenta no pertenece a esta empresa"}
        if str(account.get("status") or "") == "closed":
            return {"ok": False, "error": "cuenta cerrada, no acepta movimientos"}

        current_balance = money(account.get("current_balance") or 0)
        balance_after = round(current_balance + amount if movement_type == "entrada" else current_balance - amount, 2)

        row = {
            **identity_row(ctx),
            "account_id": account["id"],
            "account_folio": account["folio"],
            "movement_type": movement_type,
            "source_type": source_type,
            "source_id": blank(context.get("source_id")),
            "source_folio": blank(context.get("source_folio")),
            "amount": amount,
            "balance_after": balance_after,
            "movement_date": str(context.get("movement_date") or today_iso()),
            "notes": blank(context.get("notes")),
            "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
        }

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se registro movimiento",
                "data": {
                    "movement": {"folio": "BAM-DRYRUN", **row},
                    "balance_before": current_balance,
                    "balance_after": balance_after,
                },
            }

        folio_result = reserve_folio(ctx, "banks_movements", "BAM")
        if not folio_result.get("ok"):
            return folio_result
        row["folio"] = folio_result["data"]["folio"]

        result = db.rest_insert("banks_movements", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        movement = data[0] if isinstance(data, list) and data else data

        db.rest_update("banks_accounts", {"current_balance": balance_after, "updated_at": "now()"}, {"id": account["id"]})

        return {
            "ok": True,
            "data": {
                "movement": movement,
                "balance_before": current_balance,
                "balance_after": balance_after,
            },
        }
