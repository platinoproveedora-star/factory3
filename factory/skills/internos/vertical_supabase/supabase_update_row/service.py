"""Service for supabase_update_row - updates rows through Supabase REST."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class SupabaseUpdateRowService:

    def ejecutar(self, context: dict) -> dict:
        table = context.get("table")
        values = context.get("values")
        filters = context.get("filters")
        if not table or not _VALID_NAME.match(str(table)):
            return {"ok": False, "error": "table invalida o requerida"}
        if not isinstance(values, dict) or not values:
            return {"ok": False, "error": "values debe ser diccionario no vacio"}
        if not isinstance(filters, dict) or not filters:
            return {"ok": False, "error": "filters debe ser diccionario no vacio"}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo nada", "data": {"table": table, "values": values, "filters": filters}}
        return SupabaseClient(context).rest_update(table, values, filters)
