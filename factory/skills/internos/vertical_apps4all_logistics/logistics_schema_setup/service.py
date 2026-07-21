from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import create_sql, db, is_dry_run, resolve_context


class LogisticsSchemaSetupService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        sql = create_sql(ctx["schema"])
        if is_dry_run(context):
            return {"ok": True, "message": "dry_run: no se ejecuto SQL", "data": {"schema": ctx["schema"], "sql": sql}}
        result = db(ctx).management_query(sql, read_only=False)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"schema": ctx["schema"], "result": result.get("data")}}
