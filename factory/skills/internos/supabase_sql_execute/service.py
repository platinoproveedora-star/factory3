"""Service for supabase_sql_execute - runs arbitrary SQL via Supabase Management API."""

from __future__ import annotations

from factory.engine import SupabaseClient


class SupabaseSqlExecuteService:

    def ejecutar(self, context: dict) -> dict:
        sql = context.get("sql", "").strip()
        statements = context.get("statements")

        if statements and isinstance(statements, list):
            sql = "\n\n".join(s.strip() for s in statements if s.strip())

        if not sql:
            return {"ok": False, "error": "sql o statements es requerido"}

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
