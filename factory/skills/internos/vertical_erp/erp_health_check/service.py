from __future__ import annotations

import importlib.util
import re
from pathlib import Path


REQUIRED_IDENTITY = ["empresa_id", "project_code", "module_code"]
REQUIRED_TABLE_COLUMNS = ["id", "folio", "empresa_id", "project_code", "module_code"]
RECOMMENDED_USER_COLUMNS = ["global_user_id", "phone", "email"]
RECOMMENDED_LINK_COLUMNS = [
    "cost_center_id",
    "customer_id",
    "supplier_id",
    "sales_order_id",
    "purchase_order_id",
    "asset_id",
    "erp_tags",
]


class ErpHealthCheckService:
    def ejecutar(self, context: dict) -> dict:
        project = context.get("project") if isinstance(context.get("project"), dict) else {}
        identity = self._identity(context, project)
        tables = self._tables(context)
        schema_sql = str(context.get("schema_sql") or context.get("sql") or "")

        issues: list[str] = []
        warnings: list[str] = []
        checks: dict[str, object] = {}

        self._check_identity(identity, issues, warnings, checks)
        self._check_project(project, context, warnings, checks)

        if tables:
            self._check_tables(tables, issues, warnings, checks)
        elif schema_sql:
            parsed = self._parse_schema_sql(schema_sql)
            self._check_tables(parsed, issues, warnings, checks)
            checks["schema_sql_parsed_tables"] = sorted(parsed.keys())
        else:
            warnings.append("No se recibieron tables ni schema_sql; auditoria de columnas no ejecutada")

        self._check_no_hardcodes(context, issues, warnings, checks)

        score = self._score(issues, warnings)
        return {
            "ok": not issues,
            "data": {
                "ready": not issues,
                "score": score,
                "issues": issues,
                "warnings": warnings,
                "identity": identity,
                "checks": checks,
            },
        }

    def _identity(self, context: dict, project: dict) -> dict:
        empresa_id = (
            context.get("empresa_id")
            or context.get("company_id")
            or project.get("empresa_id")
            or project.get("company_id")
            or ""
        )
        return {
            "empresa_id": str(empresa_id).strip(),
            "company_id": str(empresa_id).strip(),
            "legacy_client_id": str(context.get("legacy_client_id") or project.get("legacy_client_id") or context.get("client_id") or "").strip(),
            "project_code": str(context.get("project_code") or project.get("project_code") or "").strip(),
            "module_code": str(context.get("module_code") or project.get("module_code") or "").strip(),
            "schema": str(context.get("schema") or context.get("supabase_schema") or project.get("supabase_schema") or "").strip(),
        }

    def _tables(self, context: dict) -> dict[str, list[str]]:
        raw = context.get("tables") or {}
        if not isinstance(raw, dict):
            return {}

        tables: dict[str, list[str]] = {}
        for table_name, value in raw.items():
            if isinstance(value, dict):
                columns = value.get("columns") or []
            else:
                columns = value
            if isinstance(columns, list):
                tables[str(table_name)] = [str(col) for col in columns]
        return tables

    def _check_identity(self, identity: dict, issues: list[str], warnings: list[str], checks: dict) -> None:
        missing = [field for field in REQUIRED_IDENTITY if not identity.get(field)]
        if missing:
            issues.append(f"Identidad incompleta: {', '.join(missing)}")
        if identity.get("legacy_client_id") and identity.get("legacy_client_id") == identity.get("empresa_id"):
            warnings.append("legacy_client_id es igual a empresa_id; revisar alias legacy")
        checks["identity_complete"] = not missing

    def _check_project(self, project: dict, context: dict, warnings: list[str], checks: dict) -> None:
        project_path = context.get("project_path") or project.get("folder") or ""
        if project_path:
            checks["project_path"] = str(project_path)
            checks["project_path_exists"] = Path(project_path).exists()
        if not project:
            warnings.append("No se recibio project.json/project; se audita solo por contexto")
        elif not project.get("erp_ready"):
            warnings.append("project.erp_ready no esta marcado como true")

    def _check_tables(self, tables: dict[str, list[str]], issues: list[str], warnings: list[str], checks: dict) -> None:
        table_results = {}
        for table_name, columns in tables.items():
            column_set = set(columns)
            missing = [col for col in REQUIRED_TABLE_COLUMNS if col not in column_set]
            if missing:
                issues.append(f"{table_name}: faltan columnas ERP {', '.join(missing)}")

            lower_name = table_name.lower()
            recommended_missing = []
            if "usuario" in lower_name or "user" in lower_name:
                recommended_missing = [col for col in RECOMMENDED_USER_COLUMNS if col not in column_set]
            if lower_name.endswith("gastos") or ".gastos" in lower_name or lower_name == "gastos":
                recommended_missing = [col for col in RECOMMENDED_LINK_COLUMNS if col not in column_set]
            if recommended_missing:
                warnings.append(f"{table_name}: recomendadas faltantes {', '.join(recommended_missing)}")

            table_results[table_name] = {
                "ok": not missing,
                "missing_required": missing,
                "missing_recommended": recommended_missing,
            }
        checks["tables"] = table_results

    def _check_no_hardcodes(self, context: dict, issues: list[str], warnings: list[str], checks: dict) -> None:
        raw_paths = context.get("hardcode_audit_paths") or context.get("scan_paths") or []
        project_path = context.get("project_path") or ""
        if not raw_paths and project_path:
            raw_paths = [project_path]
        if not raw_paths:
            warnings.append("No se recibieron hardcode_audit_paths; auditoria anti-hardcode no ejecutada")
            checks["no_hardcode_audit"] = {"executed": False}
            return

        service_path = Path(__file__).resolve().parents[1] / "erp_no_hardcode_audit" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_no_hardcode_audit_service", service_path)
        if spec is None or spec.loader is None:
            warnings.append("No se pudo cargar erp_no_hardcode_audit")
            checks["no_hardcode_audit"] = {"executed": False}
            return
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.ErpNoHardcodeAuditService().ejecutar({**context, "paths": raw_paths, "include_allowed": False})
        data = result.get("data") or {}
        summary = data.get("summary") or {}
        checks["no_hardcode_audit"] = {
            "executed": True,
            "summary": summary,
            "blockers": data.get("blockers") or [],
            "warnings": data.get("warnings") or [],
        }
        blockers = int(summary.get("blockers") or 0)
        warn_count = int(summary.get("warnings") or 0)
        if blockers:
            issues.append(f"Hardcodes bloqueantes detectados: {blockers}")
        if warn_count:
            warnings.append(f"Hardcodes/revisiones detectadas: {warn_count}")

    def _parse_schema_sql(self, schema_sql: str) -> dict[str, list[str]]:
        tables: dict[str, list[str]] = {}
        pattern = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([\w.]+)\s*\((.*?)\);", re.IGNORECASE | re.DOTALL)
        for match in pattern.finditer(schema_sql):
            table_name = match.group(1)
            body = match.group(2)
            columns = []
            for raw_line in body.splitlines():
                line = raw_line.strip().rstrip(",")
                if not line or line.startswith("--"):
                    continue
                first = line.split(None, 1)[0].strip('"')
                if first.lower() in {"constraint", "primary", "foreign", "unique", "check"}:
                    continue
                columns.append(first)
            tables[table_name] = columns
        return tables

    def _score(self, issues: list[str], warnings: list[str]) -> int:
        return max(0, 100 - len(issues) * 25 - len(warnings) * 8)
