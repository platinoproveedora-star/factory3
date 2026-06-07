from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


REQUIRED_PROJECT_FIELDS = ["company_id", "project_code", "module_code", "schema"]


class FactoryProjectContextResolveService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = self._repo_root()
        company = self._load_company(context, repo_root)
        project = self._load_project(context, repo_root)
        modules_file = self._load_modules(context, repo_root, company, project)
        modules = modules_file.get("modules") or []
        module_by_code = {str(row.get("module_code") or ""): row for row in modules if isinstance(row, dict)}
        module_by_project = {str(row.get("project_code") or ""): row for row in modules if isinstance(row, dict)}

        target_project_code = self._first(context.get("project_code"), project.get("project_code"), context.get("target_project_code"))
        target_module_code = self._first(context.get("module_code"), project.get("module_code"), context.get("target_module_code"))
        module_row = module_by_project.get(target_project_code) or module_by_code.get(target_module_code) or {}

        company_id = self._first(
            context.get("company_id"),
            context.get("empresa_id"),
            project.get("company_id"),
            project.get("empresa_id"),
            company.get("company_id"),
            company.get("empresa_id"),
            modules_file.get("company_id"),
            os.getenv("FACTORY_COMPANY_ID"),
        )
        schema = self._first(
            context.get("schema"),
            context.get("supabase_schema"),
            context.get("db_schema"),
            project.get("schema"),
            project.get("supabase_schema"),
            module_row.get("schema"),
            os.getenv("FACTORY_SUPABASE_SCHEMA"),
        )
        project_code = self._first(target_project_code, module_row.get("project_code"))
        module_code = self._first(target_module_code, module_row.get("module_code"))

        module_schemas = {
            str(row.get("module_code")): row.get("schema")
            for row in modules
            if isinstance(row, dict) and row.get("module_code") and row.get("schema")
        }
        module_projects = {
            str(row.get("module_code")): row.get("project_code")
            for row in modules
            if isinstance(row, dict) and row.get("module_code") and row.get("project_code")
        }
        project_schemas = {
            str(row.get("project_code")): row.get("schema")
            for row in modules
            if isinstance(row, dict) and row.get("project_code") and row.get("schema")
        }

        issues = []
        for field, value in {"company_id": company_id, "project_code": project_code, "module_code": module_code, "schema": schema}.items():
            if not value:
                issues.append(f"{field} requerido; no usar defaults de cliente")

        project_validation = self._validate_project(project)
        warnings = []
        if not project:
            warnings.append("project.json no encontrado; proyecto no valido para cierre")
        elif project_validation:
            issues.extend(project_validation)

        data = {
            "company_id": company_id or None,
            "empresa_id": company_id or None,
            "project_code": project_code or None,
            "module_code": module_code or None,
            "schema": schema or None,
            "supabase_schema": schema or None,
            "platform": self._first(context.get("platform"), project.get("platform"), module_row.get("platform")) or None,
            "requires_env": context.get("requires_env") or project.get("requires_env") or module_row.get("requires_env") or [],
            "module_schemas": module_schemas,
            "module_projects": module_projects,
            "project_schemas": project_schemas,
            "folder": self._first(context.get("folder"), project.get("folder"), module_row.get("folder")) or None,
            "dashboard_url": self._first(context.get("dashboard_url"), project.get("dashboard_url"), module_row.get("dashboard_url")) or None,
            "factory_api_url": self._first(context.get("factory_api_url"), os.getenv("FACTORY_API_URL")) or None,
            "company": company,
            "project": project,
            "module": module_row,
            "company_path": str(company.get("_path")) if company.get("_path") else None,
            "project_path": str(project.get("_path")) if project.get("_path") else None,
            "modules_path": str(modules_file.get("_path")) if modules_file.get("_path") else None,
            "ready": not issues,
            "issues": issues,
            "warnings": warnings,
        }
        return {"ok": not issues, "data": data, "error": "; ".join(issues) if issues else None}

    def _validate_project(self, project: dict) -> list[str]:
        return [f"project.json falta {field}" for field in REQUIRED_PROJECT_FIELDS if not self._first(project.get(field), project.get("supabase_schema") if field == "schema" else None)]

    def _load_company(self, context: dict, repo_root: Path) -> dict:
        company_path = self._first(context.get("company_json_path"), context.get("company_path"))
        candidates: list[Path] = []
        if company_path:
            path = Path(str(company_path))
            candidates.append(path if path.is_absolute() else repo_root / path)
        company_id = self._first(context.get("company_id"), context.get("empresa_id"))
        if company_id:
            candidates.append(repo_root / "companies" / company_id / "company.json")
        for candidate in candidates:
            data = self._read_json(candidate)
            if data is not None:
                data["_path"] = str(candidate)
                return data
        return {}

    def _load_project(self, context: dict, repo_root: Path) -> dict:
        project_path = self._first(context.get("project_json_path"), context.get("project_path"))
        candidates: list[Path] = []
        if project_path:
            path = Path(str(project_path))
            candidates.append(path if path.is_absolute() else repo_root / path)
        company_id = self._first(context.get("company_id"), context.get("empresa_id"))
        project_code = self._first(context.get("project_code"), context.get("target_project_code"))
        if company_id and project_code:
            base = repo_root / "companies" / company_id / "projects"
            if base.exists():
                candidates.extend(sorted(base.glob(f"{project_code}*/project.json")))
        for candidate in candidates:
            if candidate.is_dir():
                candidate = candidate / "project.json"
            data = self._read_json(candidate)
            if data is not None:
                data["_path"] = str(candidate)
                return data
        return {}

    def _load_modules(self, context: dict, repo_root: Path, company: dict, project: dict) -> dict:
        explicit = self._first(context.get("modules_json_path"), context.get("modules_path"))
        candidates: list[Path] = []
        if explicit:
            path = Path(str(explicit))
            candidates.append(path if path.is_absolute() else repo_root / path)
        company_id = self._first(context.get("company_id"), context.get("empresa_id"), project.get("company_id"), company.get("company_id"))
        if company_id:
            projects_dir = repo_root / "companies" / company_id / "projects"
            if projects_dir.exists():
                candidates.extend(sorted(projects_dir.glob("*/modules.json")))
        for candidate in candidates:
            data = self._read_json(candidate)
            if data is not None:
                data["_path"] = str(candidate)
                return data
        return {}

    def _read_json(self, path: Path) -> dict | None:
        try:
            if not path.exists() or not path.is_file():
                return None
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[5]

    def _first(self, *values: Any) -> str:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""
