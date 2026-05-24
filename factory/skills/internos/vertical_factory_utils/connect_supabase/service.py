"""Service for connect_supabase - validates Supabase credentials."""

from __future__ import annotations

from factory.engine import SupabaseClient


class ConnectSupabaseService:

    def ejecutar(self, context: dict) -> dict:
        client = SupabaseClient(context)
        mode = context.get("mode", "config")
        if mode not in {"config", "rest", "management", "full"}:
            return {"ok": False, "error": "mode debe ser config, rest, management o full"}

        require_rest = mode in {"rest", "full"}
        require_management = mode in {"management", "full"}
        check = client.check_config(require_rest=require_rest, require_management=require_management)
        if not check.get("ok"):
            return check
        if mode == "config" and not client.public_config().get("url"):
            return {"ok": False, "error": "SUPABASE_URL no configurada"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "configuracion Supabase detectada", "data": check["data"]}

        if require_management:
            result = client.management_query("select 1 as ok", read_only=True)
            if not result.get("ok"):
                return result

        return {"ok": True, "message": "Supabase conectado", "data": client.public_config()}
