"""Expone un schema en Supabase Data API sin sobrescribir los existentes."""
from __future__ import annotations
from factory.engine import SupabaseClient


class SupabaseExposeSchemaService:

    def ejecutar(self, context: dict) -> dict:
        schema = str(context.get("schema") or "").strip()
        if not schema:
            return {"ok": False, "error": "schema es requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"schema": schema}}

        db = SupabaseClient(context)

        # 1. Leer schemas actualmente expuestos
        result = db.management_query(
            """
SELECT replace(setting, 'pgrst.db_schemas=', '') AS schemas
FROM pg_db_role_setting s
JOIN pg_roles r ON r.oid = s.setrole
CROSS JOIN LATERAL unnest(s.setconfig) AS setting
WHERE r.rolname = 'authenticator'
  AND setting LIKE 'pgrst.db_schemas=%'
LIMIT 1;
""",
            read_only=True,
        )
        if not result.get("ok"):
            return {"ok": False, "error": f"No se pudo leer schemas actuales: {result.get('error')}"}

        current_raw = ""
        try:
            rows = result.get("data") or []
            if rows and isinstance(rows, list):
                current_raw = rows[0].get("schemas") or ""
        except Exception:
            pass

        # Siempre incluir los bases + los existentes + el nuevo
        base = ["public", "storage", "graphql_public"]
        existing = [s.strip() for s in current_raw.split(",") if s.strip()]
        all_schemas = list(dict.fromkeys(base + existing + [schema]))  # preserva orden, sin duplicados

        schemas_str = ",".join(all_schemas)

        # 2. Aplicar y recargar
        sql = f"""
ALTER ROLE authenticator SET pgrst.db_schemas = '{schemas_str}';
NOTIFY pgrst, 'reload config';
NOTIFY pgrst, 'reload schema';
"""
        apply = db.management_query(sql)
        if not apply.get("ok"):
            return {"ok": False, "error": f"No se pudo aplicar: {apply.get('error')}"}

        return {
            "ok": True,
            "message": f"Schema '{schema}' expuesto correctamente",
            "data": {
                "schema_added": schema,
                "all_schemas": all_schemas,
                "schemas_string": schemas_str,
            },
        }
