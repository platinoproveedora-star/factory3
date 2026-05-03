"""Service for supabase_query_table - reads rows through Supabase REST."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class SupabaseQueryTableService:

    def ejecutar(self, context: dict) -> dict:
        table = context.get("table")
        if not table or not _VALID_NAME.match(str(table)):
            return {"ok": False, "error": "table invalida o requerida"}
        filters = context.get("filters", {})
        if filters and not isinstance(filters, dict):
            return {"ok": False, "error": "filters debe ser diccionario"}
        limit = context.get("limit")
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            return {"ok": False, "error": "limit debe ser entero positivo"}
        select = context.get("select", "*")
        order = context.get("order")
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se consulto nada",
                "data": {"table": table, "select": select, "filters": filters, "limit": limit, "order": order},
            }
        return SupabaseClient(context).rest_select(table, filters=filters, select=select, limit=limit, order=order)
