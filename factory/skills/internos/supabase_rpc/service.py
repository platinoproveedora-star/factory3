"""Service for supabase_rpc - calls Postgres functions through Supabase REST."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class SupabaseRpcService:

    def ejecutar(self, context: dict) -> dict:
        function_name = context.get("function_name") or context.get("name")
        params = context.get("params", {})
        if not function_name or not _VALID_NAME.match(str(function_name)):
            return {"ok": False, "error": "function_name invalido o requerido"}
        if params and not isinstance(params, dict):
            return {"ok": False, "error": "params debe ser diccionario"}
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se llamo RPC",
                "data": {"function_name": function_name, "params": params},
            }
        return SupabaseClient(context).rpc(function_name, params)
