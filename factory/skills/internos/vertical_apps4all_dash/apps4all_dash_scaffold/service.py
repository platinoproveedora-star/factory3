from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
DEFAULT_TEMPLATE = Path("factory/skills/internos/vertical_apps4all_dash/templates/base_dashboard")
SKIP_DIRS = {"node_modules", ".next", ".git", "dist", "build"}
SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]*$")
CODE_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class Apps4AllDashScaffoldService:
    def ejecutar(self, context: dict) -> dict:
        company_id = self._text(context.get("company_id") or context.get("empresa_id"))
        project_code = self._text(context.get("project_code"))
        module_code = self._text(context.get("module_code"))
        schema = self._text(context.get("schema") or context.get("supabase_schema"))
        dashboard_name = self._text(context.get("dashboard_name") or f"{module_code} Dashboard")
        target_path = self._target(context)
        template_path = self._path(context.get("template_path") or DEFAULT_TEMPLATE)
        dry_run = context.get("dry_run", True)

        errors = self._validate(company_id, project_code, module_code, schema, target_path, template_path)
        if errors:
            return {"ok": False, "error": "; ".join(errors)}

        planned = {
            "target_path": str(target_path.relative_to(ROOT)),
            "template_path": str(template_path.relative_to(ROOT)),
            "dashboard_name": dashboard_name,
            "company_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
            "schema": schema,
        }
        if dry_run:
            return {"ok": True, "data": {"planned": planned, "dry_run": True}}

        if target_path.exists() and any(target_path.iterdir()) and not context.get("overwrite", False):
            return {"ok": False, "error": "target_path ya existe; usa overwrite=true si quieres reemplazar"}

        if target_path.exists() and context.get("overwrite", False):
            shutil.rmtree(target_path)
        self._copy_template(template_path, target_path)
        self._write_project_files(target_path, company_id, project_code, module_code, schema, dashboard_name)
        return {"ok": True, "data": {"written": planned}}

    def _validate(self, company_id: str, project_code: str, module_code: str, schema: str, target_path: Path, template_path: Path) -> list[str]:
        errors = []
        if not company_id.startswith("EMP_"):
            errors.append("company_id requerido con prefijo de empresa valido")
        if not project_code:
            errors.append("project_code requerido")
        if not module_code or not CODE_RE.match(module_code):
            errors.append("module_code invalido")
        if not schema or not SCHEMA_RE.match(schema):
            errors.append("schema invalido")
        if not self._inside_repo(target_path):
            errors.append("target_path fuera del repo")
        if not template_path.exists():
            errors.append("template_path no existe")
        return errors

    def _target(self, context: dict) -> Path:
        raw = context.get("target_path")
        if raw:
            return self._path(raw)
        company_id = self._text(context.get("company_id") or context.get("empresa_id"))
        project_code = self._text(context.get("project_code"))
        return ROOT / "companies" / company_id / "projects" / f"{project_code}_DASHBOARD"

    def _path(self, raw) -> Path:
        path = Path(str(raw))
        return path if path.is_absolute() else ROOT / path

    def _copy_template(self, template: Path, target: Path) -> None:
        def ignore(_dir, names):
            return [name for name in names if name in SKIP_DIRS]

        shutil.copytree(template, target, ignore=ignore)

    def _write_project_files(self, target: Path, company_id: str, project_code: str, module_code: str, schema: str, dashboard_name: str) -> None:
        project = {
            "company_id": company_id,
            "project_code": project_code,
            "project_name": dashboard_name,
            "module_code": module_code,
            "schema": schema,
            "platform": "vercel",
            "requires_env": [
                "FACTORY_API_URL",
                "FACTORY_RUN_SECRET",
                "PLATFORM_JWT_SECRET",
                "PLATFORM_SUPABASE_URL",
                "PLATFORM_SUPABASE_SERVICE_ROLE_KEY",
            ],
        }
        (target / "project.json").write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        (target / ".env.example").write_text(
            "\n".join(
                [
                    "FACTORY_API_URL=",
                    "FACTORY_RUN_SECRET=",
                    "PLATFORM_JWT_SECRET=",
                    "PLATFORM_SUPABASE_URL=",
                    "PLATFORM_SUPABASE_SERVICE_ROLE_KEY=",
                    "NEXT_PUBLIC_APPS4ALL_URL=",
                    f"{module_code.upper()}_SCHEMA={schema}",
                    f"{module_code.upper()}_MODULE_CODE={module_code}",
                    f"{module_code.upper()}_PROJECT_CODE={project_code}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _inside_repo(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(ROOT.resolve())
            return True
        except ValueError:
            return False

    def _text(self, value) -> str:
        return str(value or "").strip()
