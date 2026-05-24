"""Creates base Supabase tables for a new factory."""
from __future__ import annotations
import json
import urllib.request

TABLES_SQL = {
    "sessions": """
        CREATE TABLE IF NOT EXISTS sessions (
            chat_id TEXT PRIMARY KEY,
            data JSONB NOT NULL DEFAULT '{}',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """,
    "agent_memory": """
        CREATE TABLE IF NOT EXISTS agent_memory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_chat
            ON agent_memory (agent_id, chat_id);
    """,
}


class NewFactorySupabaseService:

    def ejecutar(self, context: dict) -> dict:
        ok, error = self._validar(context)
        if not ok:
            return {"ok": False, "error": error}
        if context.get("dry_run"):
            tables = context.get("tables", list(TABLES_SQL.keys()))
            return {"ok": True, "message": "dry_run", "data": {"tables": tables}}

        supabase_url = context["supabase_url"].rstrip("/")
        access_token = context["supabase_access_token"]
        project_ref = context["supabase_project_ref"]
        tables = context.get("tables", list(TABLES_SQL.keys()))

        created = []
        errors = []
        for table in tables:
            sql = TABLES_SQL.get(table)
            if not sql:
                errors.append(f"tabla desconocida: {table}")
                continue
            try:
                self._exec_sql(supabase_url, access_token, project_ref, sql.strip())
                created.append(table)
            except Exception as exc:
                errors.append(f"{table}: {exc}")

        ok_result = len(created) > 0 and len(errors) == 0
        return {
            "ok": ok_result,
            "message": f"{len(created)} tablas creadas" + (f", {len(errors)} errores" if errors else ""),
            "data": {"tables_created": created, "errors": errors},
        }

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        for field in ("supabase_url", "supabase_access_token", "supabase_project_ref"):
            if not context.get(field):
                return False, f"{field} es requerido"
        return True, None

    def _exec_sql(self, url: str, token: str, project_ref: str, sql: str) -> dict:
        data = json.dumps({"query": sql}).encode()
        req = urllib.request.Request(
            f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
            data=data, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}
