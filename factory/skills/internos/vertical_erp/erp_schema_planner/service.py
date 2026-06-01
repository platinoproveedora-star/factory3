from __future__ import annotations

import re


VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class ErpSchemaPlannerService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        project_code = str(context.get("project_code") or "").strip()
        module_code = str(context.get("module_code") or "").strip()
        schema = str(context.get("schema") or context.get("supabase_schema") or "").strip()
        tables = context.get("tables") or []
        dry_run = context.get("dry_run", True)

        issues = []
        if not empresa_id:
            issues.append("empresa_id/company_id requerido")
        if not project_code:
            issues.append("project_code requerido")
        if not module_code:
            issues.append("module_code requerido")
        if not self._valid_name(schema):
            issues.append("schema invalido o faltante")
        if not isinstance(tables, list) or not tables:
            issues.append("tables requerido como lista")

        table_sql = []
        if not issues:
            for table in tables:
                planned = self._table_sql(schema, empresa_id, project_code, module_code, table, issues)
                if planned:
                    table_sql.append(planned)

        sql = "\n\n".join([f"CREATE SCHEMA IF NOT EXISTS {schema};", *table_sql]) if not issues else ""
        return {
            "ok": not issues,
            "data": {
                "dry_run": dry_run,
                "schema": schema or None,
                "tables_planned": len(table_sql),
                "sql": sql,
                "issues": issues,
                "ready": not issues,
            },
        }

    def _table_sql(
        self,
        schema: str,
        empresa_id: str,
        project_code: str,
        module_code: str,
        table: dict,
        issues: list[str],
    ) -> str:
        if not isinstance(table, dict):
            issues.append("table debe ser dict")
            return ""
        name = str(table.get("name") or "").strip()
        if not self._valid_name(name):
            issues.append(f"tabla invalida: {name}")
            return ""

        columns = table.get("columns") or []
        if not isinstance(columns, list):
            issues.append(f"{name}: columns debe ser lista")
            return ""

        column_lines = [
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid()",
            "    folio text UNIQUE NOT NULL",
            f"    empresa_id text NOT NULL DEFAULT '{empresa_id}'",
            f"    project_code text NOT NULL DEFAULT '{project_code}'",
            f"    module_code text NOT NULL DEFAULT '{module_code}'",
        ]
        for column in columns:
            if isinstance(column, dict):
                col_name = str(column.get("name") or "").strip()
                col_type = str(column.get("type") or "text").strip()
                nullable = bool(column.get("nullable", True))
                default = column.get("default")
                if not self._valid_name(col_name):
                    issues.append(f"{name}: columna invalida {col_name}")
                    continue
                line = f"    {col_name} {col_type}"
                if not nullable:
                    line += " NOT NULL"
                if default is not None:
                    line += f" DEFAULT {default}"
                column_lines.append(line)
        column_lines.extend([
            "    erp_tags jsonb NOT NULL DEFAULT '{}'",
            "    metadata jsonb NOT NULL DEFAULT '{}'",
            "    created_at timestamptz NOT NULL DEFAULT now()",
            "    updated_at timestamptz",
        ])
        return f"CREATE TABLE IF NOT EXISTS {schema}.{name} (\n" + ",\n".join(column_lines) + "\n);"

    def _valid_name(self, value: str) -> bool:
        return bool(value and VALID_NAME.match(value))

