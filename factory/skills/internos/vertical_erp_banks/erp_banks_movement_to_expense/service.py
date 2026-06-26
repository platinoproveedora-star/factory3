from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _banks_common import SupabaseClient, blank, money, reserve_folio  # noqa: E402


def _text(value: Any) -> str:
    return str(value or "").strip()


class ErpBanksMovementToExpenseService:
    def ejecutar(self, context: dict) -> dict:
        resolved = self._resolve_context(context)
        if not resolved.get("ok"):
            return resolved
        ctx = resolved["data"]

        movement = self._find_movement(ctx)
        if not movement:
            return {"ok": False, "error": "movimiento no encontrado"}
        if movement.get("reversal_of_movement_id"):
            return {"ok": False, "error": "no se puede crear gasto desde un movimiento de reversa"}
        if movement.get("authorization_status") == "rechazado":
            return {"ok": False, "error": "no se puede crear gasto desde un movimiento rechazado"}
        if self._movement_already_from_expense(movement):
            return {"ok": False, "error": "este movimiento ya viene de gastos"}
        if movement.get("reconciliation_status") == "revisado_conciliado":
            existing = self._find_existing_expense(ctx, movement)
            if existing:
                return {"ok": True, "data": {"expense": existing, "movement": movement, "idempotent": True}}
            return {"ok": False, "error": "este movimiento ya fue revisado o conciliado"}
        if movement.get("movement_type") != "salida" and not ctx["allow_income_as_expense"]:
            return {"ok": False, "error": "solo movimientos de salida se convierten a gasto"}

        existing = self._find_existing_expense(ctx, movement)
        if existing:
            self._mark_movement_reviewed(ctx, movement, dry_run=bool(context.get("dry_run", True)))
            return {"ok": True, "data": {"expense": existing, "movement": movement, "idempotent": True}}

        category = self._find_category(ctx)
        if not category:
            return {"ok": False, "error": "categoria no encontrada"}
        user = self._find_user(ctx)
        if not user:
            return {"ok": False, "error": "usuario no encontrado"}
        account = self._find_account(ctx, movement)

        description = _text(ctx.get("descripcion") or ctx.get("description") or movement.get("notes"))
        if not description:
            metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
            description = _text(metadata.get("description") or metadata.get("concepto") or metadata.get("reference"))
        if not description:
            description = f"Movimiento bancario {movement.get('folio')}"

        preview = {
            "movement": movement,
            "expense": {
                "folio": "GAS-DRYRUN",
                "usuario_id": user["id"],
                "categoria_id": category["id"],
                "monto": money(movement.get("amount")),
                "descripcion": description,
                "fecha": movement.get("movement_date"),
                "cta_retiro_id": movement.get("account_id"),
                "cta_retiro_folio": movement.get("account_folio"),
                "cta_retiro_nombre": (account or {}).get("account_name"),
            },
        }
        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, **preview}}

        folio_result = self._reserve_expense_folio(
            {
                "schema": ctx["expenses_schema"],
                "company_id": ctx["company_id"],
                "project_code": ctx["expenses_project_code"],
                "module_code": ctx["expenses_module_code"],
            },
            "gastos",
            "GAS",
        )
        if not folio_result.get("ok"):
            return folio_result

        erp_tags = {
            "source": "bank_movement",
            "bank_movement_id": movement.get("id"),
            "bank_movement_folio": movement.get("folio"),
            "bank_movement_type": movement.get("movement_type"),
            "bank_source_type": movement.get("source_type"),
            "bank_source_module": movement.get("source_module"),
            "bank_source_folio": movement.get("source_folio"),
            "clave_rastreo": movement.get("clave_rastreo"),
        }
        row = {
            "folio": folio_result["data"]["folio"],
            "empresa_id": ctx["company_id"],
            "project_code": ctx["expenses_project_code"],
            "module_code": ctx["expenses_module_code"],
            "usuario_id": user["id"],
            "categoria_id": category["id"],
            "monto": money(movement.get("amount")),
            "descripcion": description,
            "fecha": movement.get("movement_date"),
            "metodo_captura": "bank_movement",
            "cta_retiro_id": movement.get("account_id"),
            "cta_retiro_folio": movement.get("account_folio"),
            "cta_retiro_nombre": (account or {}).get("account_name") or movement.get("account_folio"),
            "erp_tags": erp_tags,
        }
        inserted = self._insert_expense(ctx, row)
        if not inserted.get("ok"):
            return inserted
        expense = (inserted.get("data") or [{}])[0]
        self._insert_event(ctx, expense, user, movement, erp_tags)
        self._mark_movement_reviewed(ctx, movement, dry_run=False)
        return {"ok": True, "data": {"expense": expense, "movement": movement, "created": True}}

    def _resolve_context(self, context: dict) -> dict:
        banks_schema = _text(context.get("banks_schema") or context.get("schema"))
        expenses_schema = _text(context.get("expenses_schema"))
        company_id = _text(context.get("company_id") or context.get("empresa_id"))
        banks_project_code = _text(context.get("banks_project_code") or context.get("project_code"))
        expenses_project_code = _text(context.get("expenses_project_code"))
        movement_id = _text(context.get("movement_id"))
        missing = [
            name for name, value in {
                "banks_schema": banks_schema,
                "expenses_schema": expenses_schema,
                "company_id": company_id,
                "banks_project_code": banks_project_code,
                "expenses_project_code": expenses_project_code,
                "movement_id": movement_id,
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
                "banks_module_code": _text(context.get("banks_module_code") or "banks"),
                "expenses_project_code": expenses_project_code,
                "expenses_module_code": _text(context.get("expenses_module_code") or "gastos"),
                "movement_id": movement_id,
                "categoria_id": _text(context.get("categoria_id") or context.get("category_id")),
                "categoria": _text(context.get("categoria") or context.get("category")),
                "usuario_id": _text(context.get("usuario_id") or context.get("user_id")),
                "allow_income_as_expense": bool(context.get("allow_income_as_expense", False)),
            },
        }

    def _find_movement(self, ctx: dict) -> dict | None:
        result = SupabaseClient({"schema": ctx["banks_schema"]}).rest_select(
            "banks_movements",
            filters={"empresa_id": f"eq.{ctx['company_id']}", "id": f"eq.{ctx['movement_id']}"},
            select="id,folio,account_id,account_folio,movement_type,source_type,source_module,source_id,source_folio,amount,movement_date,reversal_of_movement_id,clave_rastreo,authorization_status,reconciliation_status,notes,metadata,created_at",
            limit=1,
        )
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "error leyendo movimiento")
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _movement_already_from_expense(self, movement: dict) -> bool:
        metadata = movement.get("metadata") if isinstance(movement.get("metadata"), dict) else {}
        return movement.get("source_module") == "expenses" or bool(metadata.get("expense_id") or metadata.get("expense_folio"))

    def _find_existing_expense(self, ctx: dict, movement: dict) -> dict | None:
        needle = {"bank_movement_id": movement.get("id")}
        result = SupabaseClient({"schema": ctx["expenses_schema"]}).rest_select(
            "gastos",
            filters={
                "empresa_id": f"eq.{ctx['company_id']}",
                "project_code": f"eq.{ctx['expenses_project_code']}",
                "erp_tags": f"cs.{json.dumps(needle, separators=(',', ':'))}",
            },
            select="id,folio,fecha,monto,descripcion,usuario_id,categoria_id,estado,cta_retiro_id,cta_retiro_folio,cta_retiro_nombre,erp_tags",
            limit=1,
        )
        if not result.get("ok"):
            return None
        rows = result.get("data") or []
        return rows[0] if rows else None

    def _find_category(self, ctx: dict) -> dict | None:
        filters = {"empresa_id": f"eq.{ctx['company_id']}"}
        if ctx.get("categoria_id"):
            filters["id"] = f"eq.{ctx['categoria_id']}"
        elif ctx.get("categoria"):
            filters["nombre"] = f"eq.{ctx['categoria']}"
        else:
            return None
        result = SupabaseClient({"schema": ctx["expenses_schema"]}).rest_select(
            "categorias_gasto",
            filters=filters,
            select="id,folio,nombre,activo",
            limit=1,
        )
        if not result.get("ok") or not result.get("data"):
            fallback = {k: v for k, v in filters.items() if k != "empresa_id"}
            result = SupabaseClient({"schema": ctx["expenses_schema"]}).rest_select(
                "categorias_gasto",
                filters=fallback,
                select="id,folio,nombre,activo",
                limit=1,
            )
        rows = result.get("data") or [] if result.get("ok") else []
        return rows[0] if rows else None

    def _find_user(self, ctx: dict) -> dict | None:
        if not ctx.get("usuario_id"):
            return None
        result = SupabaseClient({"schema": ctx["expenses_schema"]}).rest_select(
            "usuarios",
            filters={"empresa_id": f"eq.{ctx['company_id']}", "id": f"eq.{ctx['usuario_id']}"},
            select="id,folio,nombre,activo",
            limit=1,
        )
        if not result.get("ok") or not result.get("data"):
            result = SupabaseClient({"schema": ctx["expenses_schema"]}).rest_select(
                "usuarios",
                filters={"id": f"eq.{ctx['usuario_id']}"},
                select="id,folio,nombre,activo",
                limit=1,
            )
        rows = result.get("data") or [] if result.get("ok") else []
        return rows[0] if rows else None

    def _find_account(self, ctx: dict, movement: dict) -> dict | None:
        result = SupabaseClient({"schema": ctx["banks_schema"]}).rest_select(
            "banks_accounts",
            filters={"empresa_id": f"eq.{ctx['company_id']}", "id": f"eq.{movement.get('account_id')}"},
            select="id,folio,account_name,account_type,status",
            limit=1,
        )
        rows = result.get("data") or [] if result.get("ok") else []
        return rows[0] if rows else None

    def _insert_expense(self, ctx: dict, row: dict) -> dict:
        result = SupabaseClient({"schema": ctx["expenses_schema"]}).rest_insert("gastos", row)
        if result.get("ok"):
            return result
        error = str(result.get("error") or "").lower()
        optional = {"cta_retiro_id", "cta_retiro_folio", "cta_retiro_nombre", "erp_tags"}
        if "column" not in error and "schema cache" not in error and "pgrst204" not in error:
            return result
        fallback = {key: value for key, value in row.items() if key not in optional}
        return SupabaseClient({"schema": ctx["expenses_schema"]}).rest_insert("gastos", fallback)

    def _insert_event(self, ctx: dict, expense: dict, user: dict, movement: dict, tags: dict) -> None:
        folio_result = self._reserve_expense_folio(
            {
                "schema": ctx["expenses_schema"],
                "company_id": ctx["company_id"],
                "project_code": ctx["expenses_project_code"],
                "module_code": ctx["expenses_module_code"],
            },
            "gasto_eventos",
            "EVT",
        )
        if not folio_result.get("ok"):
            return
        SupabaseClient({"schema": ctx["expenses_schema"]}).rest_insert(
            "gasto_eventos",
            {
                "folio": folio_result["data"]["folio"],
                "gasto_id": expense.get("id"),
                "usuario_id": user.get("id"),
                "evento": "creado_desde_movimiento_bancario",
                "detalle": tags,
                "empresa_id": ctx["company_id"],
                "project_code": ctx["expenses_project_code"],
                "module_code": ctx["expenses_module_code"],
            },
        )

    def _reserve_expense_folio(self, context: dict, table: str, prefix: str) -> dict:
        result = reserve_folio(context, table, prefix)
        if result.get("ok"):
            return result
        error = str(result.get("error") or "")
        if "reserve_erp_folio" not in error and "PGRST202" not in error:
            return result
        legacy = self._next_table_folio(context["schema"], table, prefix)
        return {"ok": True, "data": {"folio": legacy, "scope": table, "prefix": prefix, "legacy_fallback": True}}

    def _next_table_folio(self, schema: str, table: str, prefix: str) -> str:
        result = SupabaseClient({"schema": schema}).rest_select(
            table,
            filters={"folio": f"ilike.{prefix}-%"},
            select="folio",
            limit=10000,
        )
        if not result.get("ok"):
            return f"{prefix}-001"
        max_number = 0
        max_width = 3
        for row in result.get("data") or []:
            text = str(row.get("folio") or "")
            match = re.match(rf"^{re.escape(prefix)}-(\d+)$", text)
            if not match:
                continue
            number_text = match.group(1)
            max_width = max(max_width, len(number_text))
            max_number = max(max_number, int(number_text))
        return f"{prefix}-{max_number + 1:0{max_width}d}"

    def _mark_movement_reviewed(self, ctx: dict, movement: dict, dry_run: bool) -> None:
        if dry_run:
            return
        if movement.get("reconciliation_status") == "revisado_conciliado":
            return
        SupabaseClient({"schema": ctx["banks_schema"]}).rest_update(
            "banks_movements",
            {"reconciliation_status": "revisado_conciliado"},
            {"empresa_id": ctx["company_id"], "id": movement.get("id")},
        )
