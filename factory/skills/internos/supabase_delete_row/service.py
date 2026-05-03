"""Service for supabase_delete_row - deletes rows through Supabase REST."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class SupabaseDeleteRowService:

    def ejecutar(self, context: dict) -> dict:
        table = context.get("table")
        filters = context.get("filters")
        if not table or not _VALID_NAME.match(str(table)):
            return {"ok": False, "error": "table invalida o requerida"}
        if not isinstance(filters, dict) or not filters:
            return {"ok": False, "error": "filters debe ser diccionario no vacio"}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se borro nada", "data": {"table": table, "filters": filters}}
        return SupabaseClient(context).rest_delete(table, filters)
