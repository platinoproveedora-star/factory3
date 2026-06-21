from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from factory.engine import SupabaseClient

VALID_ACTIONS = {"list", "assign", "cancel"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _money(value: Any) -> float:
    return round(float(value or 0), 2)


class ErpBanksExpenseReconcileService:
    def ejecutar(self, context: dict) -> dict:
        action = _text(context.get("action"))
        if action not in VALID_ACTIONS:
            return {"ok": False, "error": "action requerida: list | assign"}

        resolved = self._resolve_context(context)
        if not resolved.get("ok"):
            return resolved
        ctx = resolved["data"]

        if action == "list":
            return self._list(ctx, context)
        if action == "assign":
            return self._assign(ctx, context)
        return self._cancel(ctx, context)

    def _resolve_context(self, context: dict) -> dict:
        banks_schema = _text(context.get("banks_schema") or context.get("schema"))
        expenses_schema = _text(context.get("expenses_schema"))
        company_id = _text(context.get("company_id") or context.get("empresa_id"))
        banks_project_code = _text(context.get("banks_project_code") or context.get("project_code"))
        expenses_project_code = _text(context.get("expenses_project_code"))
        missing = [
            name for name, value in {
                "banks_schema": banks_schema,
                "expenses_schema": expenses_schema,
                "company_id": company_id,
                "banks_project_code": banks_project_code,
                "expenses_project_code": expenses_project_code,
            }.items() if not value
        ]
        if missing:
            return {"ok": False, "error": f"contexto incompleto: {', '.join(missing)}"}
        return {
            "ok": True,
            "data": {
                **context,
                "banks_schema": banks_schema,
                "expenses_schema": expenses_schema,
                "company_id": company_id,
                "empresa_id": company_id,
                "banks_project_code": banks_project_code,
                "expenses_project_code": expenses_project_code,
                "banks_module_code": _text(context.get("banks_module_code") or "banks"),
                "expense_module_code": _text(context.get("expense_module_code") or "gastos"),
                "expense_source_module": _text(context.get("expense_source_module") or "expenses"),
                "expense_reversal_source_module": _text(context.get("expense_reversal_source_module") or "expenses_reversal"),
                "default_source_account_name": _text(context.get("default_source_account_name")),
                "expense_counterparty_name": _text(context.get("expense_counterparty_name")),
            },
        }

    def _list(self, ctx: dict, context: dict) -> dict:
        limit = int(context.get("limit") or 200)
        expenses_db = SupabaseClient({"schema": ctx["expenses_schema"]})
        banks_db = SupabaseClient({"schema": ctx["banks_schema"]})

        expenses_res = expenses_db.rest_select(
            "gastos",
            filters={
                "empresa_id": f"eq.{ctx['company_id']}",
                "project_code": f"eq.{ctx['expenses_project_code']}",
            },
            select="id,folio,fecha,monto,descripcion,vehiculo,usuario_id,categoria_id,estado,created_at",
            order="fecha.desc,created_at.desc",
            limit=limit,
        )
        if not expenses_res.get("ok"):
            return expenses_res

        movements_res = banks_db.rest_select(
            "banks_movements",
            filters={"empresa_id": f"eq.{ctx['company_id']}"},
            select="id,folio,source_id,source_folio,source_module,source_type,movement_type,account_id,account_folio,amount,movement_date,reconciliation_status,reversal_of_movement_id,metadata,created_at",
            order="created_at.desc",
            limit=5000,
        )
        if not movements_res.get("ok"):
            return movements_res

        account = self._find_account_by_name(ctx, ctx.get("default_source_account_name"))
        movement_by_source = self._active_expense_movements(ctx, movements_res.get("data") or [])
        rows = []
        for expense in expenses_res.get("data") or []:
            linked = self._movement_for_expense(movement_by_source, expense)
            rows.append({
                **expense,
                "linked": bool(linked),
                "bank_movement": linked,
            })
        return {
            "ok": True,
            "data": {
                "expenses": rows,
                "default_source_account": account,
                "expense_counterparty_name": ctx.get("expense_counterparty_name"),
                "summary": {
                    "total": len(rows),
                    "pending": len([row for row in rows if not row["linked"]]),
                    "linked": len([row for row in rows if row["linked"]]),
                },
            },
        }

    def _assign(self, ctx: dict, context: dict) -> dict:
        expense = self._find_expense(ctx, context)
        if not expense:
            return {"ok": False, "error": "gasto no encontrado"}

        existing = self._find_existing_assignment(ctx, expense)
        if existing:
            return {"ok": True, "data": {"expense": expense, "movement_result": {"movement": existing, "idempotent": True}}}

        source_account_id = _text(context.get("source_account_id"))
        if not source_account_id:
            account = self._find_account_by_name(ctx, ctx.get("default_source_account_name"))
            source_account_id = _text((account or {}).get("id"))
        if not source_account_id:
            return {"ok": False, "error": "source_account_id requerido o cuenta default no encontrada"}

        movement_context = {
            "schema": ctx["banks_schema"],
            "company_id": ctx["company_id"],
            "project_code": ctx["banks_project_code"],
            "module_code": ctx["banks_module_code"],
            "account_id": source_account_id,
            "movement_type": "salida",
            "source_type": "pago",
            "source_module": ctx["expense_source_module"],
            "source_id": expense["id"],
            "source_folio": expense.get("folio"),
            "amount": _money(expense.get("monto")),
            "movement_date": expense.get("fecha"),
            "notes": context.get("notes") or expense.get("descripcion"),
            "metadata": {
                "expense_id": expense.get("id"),
                "expense_folio": expense.get("folio"),
                "expense_description": expense.get("descripcion"),
                "expense_vehicle": expense.get("vehiculo"),
                "expense_category_id": expense.get("categoria_id"),
                "expense_user_id": expense.get("usuario_id"),
                "expense_counterparty_name": ctx.get("expense_counterparty_name"),
                "performed_by": context.get("performed_by") or "expense_reconciliation",
                "movement_kind": "retiro",
                "counterparty_role": "destination",
            },
            "dry_run": bool(context.get("dry_run", True)),
        }

        service = self._movement_service()
        result = service.ejecutar(movement_context)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"expense": expense, "movement_result": result.get("data")}}

    def _cancel(self, ctx: dict, context: dict) -> dict:
        movement = self._find_assignment_movement(ctx, context)
        if not movement:
            return {"ok": False, "error": "asignacion no encontrada"}
        if movement.get("reversal_of_movement_id"):
            return {"ok": False, "error": "no se puede cancelar un movimiento de reversa"}
        if movement.get("movement_type") != "salida":
            return {"ok": False, "error": "solo se cancelan retiros de gastos"}

        reversal = self._find_reversal(ctx, str(movement.get("id")))
        if reversal:
            return {"ok": True, "data": {"movement": movement, "reversal_result": {"movement": reversal, "idempotent": True}}}

        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        movement_context = {
            "schema": ctx["banks_schema"],
            "company_id": ctx["company_id"],
            "project_code": ctx["banks_project_code"],
            "module_code": ctx["banks_module_code"],
            "account_id": movement.get("account_id"),
            "movement_type": "entrada",
            "source_type": "devolucion",
            "source_module": ctx["expense_reversal_source_module"],
            "source_id": str(movement.get("id")),
            "source_folio": movement.get("folio"),
            "amount": _money(movement.get("amount")),
            "movement_date": context.get("movement_date") or movement.get("movement_date"),
            "reversal_of_movement_id": movement.get("id"),
            "notes": context.get("notes") or f"Cancelacion asignacion gasto {movement.get('source_folio') or ''}".strip(),
            "metadata": {
                **metadata,
                "cancelled_assignment_movement_id": movement.get("id"),
                "cancelled_assignment_folio": movement.get("folio"),
                "performed_by": context.get("performed_by") or "conciliacion_gastos",
                "movement_kind": "cancelacion_retiro_gasto",
                "reversal_reason": context.get("reason") or "cancelacion_asignacion_gasto",
            },
            "dry_run": bool(context.get("dry_run", True)),
        }
        result = self._movement_service().ejecutar(movement_context)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"movement": movement, "reversal_result": result.get("data")}}

    def _active_expense_movements(self, ctx: dict, movements: list[dict]) -> dict[str, dict]:
        reversed_ids = {
            str(row.get("reversal_of_movement_id"))
            for row in movements
            if row.get("reversal_of_movement_id")
        }
        linked: dict[str, dict] = {}
        for row in movements:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            has_expense_metadata = bool(metadata.get("expense_id") or metadata.get("expense_folio"))
            if row.get("source_module") != ctx["expense_source_module"] and not has_expense_metadata:
                continue
            if row.get("movement_type") != "salida":
                continue
            if row.get("reversal_of_movement_id"):
                continue
            if str(row.get("id")) in reversed_ids:
                continue
            keys = [
                row.get("source_id"),
                row.get("source_folio"),
                metadata.get("expense_id"),
                metadata.get("expense_folio"),
            ]
            for key in keys:
                if key:
                    linked[str(key)] = row
        return linked

    def _movement_for_expense(self, movement_by_source: dict[str, dict], expense: dict) -> dict | None:
        for key in (expense.get("id"), expense.get("folio")):
            if key and str(key) in movement_by_source:
                return movement_by_source[str(key)]
        return None

    def _find_existing_assignment(self, ctx: dict, expense: dict) -> dict | None:
        result = SupabaseClient({"schema": ctx["banks_schema"]}).rest_select(
            "banks_movements",
            filters={"empresa_id": f"eq.{ctx['company_id']}"},
            select="id,folio,source_id,source_folio,source_module,source_type,movement_type,account_id,account_folio,amount,movement_date,reconciliation_status,reversal_of_movement_id,metadata,created_at",
            order="created_at.desc",
            limit=5000,
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "error leyendo movimientos")
        movement_by_source = self._active_expense_movements(ctx, result.get("data") or [])
        return self._movement_for_expense(movement_by_source, expense)

    def _find_assignment_movement(self, ctx: dict, context: dict) -> dict | None:
        movement_id = _text(context.get("movement_id") or context.get("assignment_movement_id"))
        if movement_id:
            result = SupabaseClient({"schema": ctx["banks_schema"]}).rest_select(
                "banks_movements",
                filters={"empresa_id": f"eq.{ctx['company_id']}", "id": f"eq.{movement_id}"},
                select="id,folio,source_id,source_folio,source_module,source_type,movement_type,account_id,account_folio,amount,movement_date,reconciliation_status,reversal_of_movement_id,metadata,created_at",
                limit=1,
            )
            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "error leyendo movimiento")
            rows = result.get("data") or []
            return rows[0] if rows else None
        expense = self._find_expense(ctx, context)
        return self._find_existing_assignment(ctx, expense) if expense else None

    def _find_reversal(self, ctx: dict, movement_id: str) -> dict | None:
        result = SupabaseClient({"schema": ctx["banks_schema"]}).rest_select(
            "banks_movements",
            filters={"empresa_id": f"eq.{ctx['company_id']}", "reversal_of_movement_id": f"eq.{movement_id}"},
            select="id,folio,source_id,source_folio,source_module,source_type,movement_type,account_id,account_folio,amount,movement_date,reconciliation_status,reversal_of_movement_id,metadata,created_at",
            order="created_at.desc",
            limit=1,
        )
        if not result.get("ok"):
            return None
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _find_expense(self, ctx: dict, context: dict) -> dict | None:
        filters = {"empresa_id": f"eq.{ctx['company_id']}"}
        expense_id = _text(context.get("expense_id"))
        expense_folio = _text(context.get("expense_folio"))
        if expense_id:
            filters["id"] = f"eq.{expense_id}"
        elif expense_folio:
            filters["folio"] = f"eq.{expense_folio}"
        else:
            return None
        result = SupabaseClient({"schema": ctx["expenses_schema"]}).rest_select(
            "gastos",
            filters=filters,
            select="id,folio,fecha,monto,descripcion,vehiculo,usuario_id,categoria_id,estado,created_at",
            limit=1,
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "error leyendo gasto")
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _find_account_by_name(self, ctx: dict, name: str | None) -> dict | None:
        if not name:
            return None
        result = SupabaseClient({"schema": ctx["banks_schema"]}).rest_select(
            "banks_accounts",
            filters={"empresa_id": f"eq.{ctx['company_id']}", "account_name": f"eq.{name}"},
            select="id,folio,account_name,current_balance,status",
            limit=1,
        )
        if not result.get("ok"):
            return None
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _movement_service(self):
        service_path = Path(__file__).resolve().parents[1] / "erp_banks_movement_record" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_banks_movement_record_service", service_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module.ErpBanksMovementRecordService()
