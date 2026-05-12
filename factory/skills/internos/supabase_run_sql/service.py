from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from engine.supabase_client import SupabaseClient


class SqlService:
    def ejecutar(self, context: dict) -> dict:
        sql = (context.get("sql") or "").strip()
        if not sql:
            return {"ok": False, "error": "parámetro 'sql' requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "sql": sql}}

        db = SupabaseClient(context)
        check = db.check_config(require_management=True)
        if not check.get("ok"):
            return check

        return db.management_query(sql)
