"""Service for supabase_schema_inspect - lists public tables and columns."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class SupabaseSchemaInspectService:

    def ejecutar(self, context: dict) -> dict:
        schema = context.get("schema", "public")
        if not _VALID_NAME.match(str(schema)):
            return {"ok": False, "error": "schema invalido"}
        sql = f"""
select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = '{schema}'
order by table_name, ordinal_position;
""".strip()
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se consulto schema", "data": {"sql": sql}}
        return SupabaseClient(context).management_query(sql, read_only=True)
