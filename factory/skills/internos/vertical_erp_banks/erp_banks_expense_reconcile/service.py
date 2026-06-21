from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from factory.engine import SupabaseClient

VALID_ACTIONS = {"list", "assign"}


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
        return self._assign(ctx, context)

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
            filters={
                "empresa_id": f"eq.{ctx['company_id']}",
                "source_module": f"eq.{ctx['expense_source_module']}",
            },
            select="id,folio,source_id,source_folio,account_id,amount,movement_date,reconciliation_status,metadata",
            order="created_at.desc",
            limit=5000,
        )
        if not movements_res.get("ok"):
            return movements_res

        account = self._find_account_by_name(ctx, ctx.get("default_source_account_name"))
        movement_by_source = {
            str(row.get("source_id") or ""): row for row in movements_res.get("data") or [] if row.get("source_id")
        }
        rows = []
        for expense in expenses_res.get("data") or []:
            linked = movement_by_source.get(str(expense.get("id")))
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
