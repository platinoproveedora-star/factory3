"""Service for supabase_insert_row - inserts rows through Supabase REST."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class SupabaseInsertRowService:

    def ejecutar(self, context: dict) -> dict:
        table = context.get("table")
        rows = context.get("rows", context.get("row"))
        if not table or not _VALID_NAME.match(str(table)):
            return {"ok": False, "error": "table invalida o requerida"}
        if not isinstance(rows, (dict, list)):
            return {"ok": False, "error": "row o rows debe ser dict o lista"}
        if isinstance(rows, list) and not all(isinstance(row, dict) for row in rows):
            return {"ok": False, "error": "rows debe contener diccionarios"}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se inserto nada", "data": {"table": table, "rows": rows}}
        return SupabaseClient(context).rest_insert(table, rows)
