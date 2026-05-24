"""Service for new_supabase_table - creates a table in Supabase via Management API."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_VALID_TYPES = {
    "text", "varchar", "integer", "bigint", "numeric", "boolean",
    "date", "timestamptz", "timestamp", "uuid", "jsonb", "float",
}


class NewSupabaseTableService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        sql = self._build_sql(context)

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se ejecuto nada", "data": {"sql": sql}}

        result = SupabaseClient(context).management_query(sql)
        if not result.get("ok"):
            result["data"] = {**result.get("data", {}), "sql": sql}
            return result
        return {
            "ok": True,
            "message": f"tabla '{context['table_name']}' creada",
            "data": {"sql": sql, "result": result.get("data")},
        }

    # --- validacion ---

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        table_name = context.get("table_name")
        if not table_name:
            return False, "table_name es requerido"
        if not _VALID_NAME.match(table_name):
            return False, "table_name debe iniciar con letra minuscula y usar solo letras, numeros o _"
        columns = context.get("columns")
        if not columns or not isinstance(columns, list):
            return False, "columns es requerido — lista de {name, type}"
        for col in columns:
            if not isinstance(col, dict):
                return False, "cada column debe ser un diccionario"
            if not col.get("name") or not _VALID_NAME.match(col["name"]):
                return False, f"column name invalido: {col.get('name')}"
            col_type = col.get("type", "").lower().split("(")[0]
            if col_type not in _VALID_TYPES:
                return False, f"tipo invalido '{col.get('type')}' — validos: {', '.join(sorted(_VALID_TYPES))}"
        return True, None

    # --- sql builder ---

    def _build_sql(self, context: dict) -> str:
        table_name = context["table_name"]
        columns = context["columns"]
        has_id = any(col.get("name") == "id" for col in columns)

        col_defs = []

        if not has_id:
            col_defs.append("id uuid primary key default gen_random_uuid()")

        for col in columns:
            col_defs.append(self._col_def(col))

        if not any(col.get("name") == "created_at" for col in columns):
            col_defs.append("created_at timestamptz default now()")

        cols_sql = ",\n  ".join(col_defs)
        return f"CREATE TABLE IF NOT EXISTS {table_name} (\n  {cols_sql}\n);"

    def _col_def(self, col: dict) -> str:
        name = col["name"]
        col_type = col.get("type", "text")
        parts = [f"{name} {col_type}"]

        if col.get("primary_key"):
            parts.append("primary key")
        if col.get("default") is not None:
            parts.append(f"default {col['default']}")
        if col.get("nullable") is False:
            parts.append("not null")
        if col.get("unique"):
            parts.append("unique")

        return " ".join(parts)
