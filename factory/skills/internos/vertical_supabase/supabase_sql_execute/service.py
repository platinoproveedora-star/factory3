"""Service for supabase_sql_execute - runs SQL via Supabase Management API."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient


_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


class SupabaseSqlExecuteService:

    def ejecutar(self, context: dict) -> dict:
        sql = context.get("sql", "").strip()
        statements = context.get("statements")

        if statements and isinstance(statements, list):
            sql = "\n\n".join(s.strip() for s in statements if s.strip())

        if not sql:
            return {"ok": False, "error": "sql o statements es requerido"}

        expose_schemas = self._schemas(context.get("expose_schemas") or context.get("schema") or [])
        if expose_schemas:
            sql = self._with_rest_exposure(sql, expose_schemas, context)

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se ejecuto nada", "data": {"sql": sql}}

        result = SupabaseClient(context).management_query(sql)
        if not result.get("ok"):
            result["data"] = {**result.get("data", {}), "sql": sql}
            return result

        return {
            "ok": True,
            "message": "SQL ejecutado correctamente",
            "data": {"sql": sql, "result": result.get("data")},
        }

    def _schemas(self, value) -> list[str]:
        if isinstance(value, str):
            value = [value]
        schemas = []
        for item in value or []:
            name = str(item).strip()
            if name and _VALID_SCHEMA.match(name) and name not in schemas:
                schemas.append(name)
        return schemas

    def _with_rest_exposure(self, sql: str, schemas: list[str], context: dict) -> str:
        base = context.get("base_schemas") or ["public", "storage", "graphql_public"]
        all_schemas = []
        for name in list(base) + schemas:
            if str(name).strip() and str(name).strip() not in all_schemas:
                all_schemas.append(str(name).strip())

        grants = []
        for schema in schemas:
            grants.extend([
                f"grant usage on schema {schema} to anon, authenticated, service_role;",
                f"grant all on all tables in schema {schema} to anon, authenticated, service_role;",
                f"grant all on all sequences in schema {schema} to anon, authenticated, service_role;",
                f"alter default privileges in schema {schema} grant all on tables to anon, authenticated, service_role;",
                f"alter default privileges in schema {schema} grant all on sequences to anon, authenticated, service_role;",
            ])

        grants.append(f"alter role authenticator set pgrst.db_schemas = '{','.join(all_schemas)}';")
        grants.append("notify pgrst, 'reload config';")
        grants.append("notify pgrst, 'reload schema';")
        return sql.rstrip() + "\n\n" + "\n".join(grants)
