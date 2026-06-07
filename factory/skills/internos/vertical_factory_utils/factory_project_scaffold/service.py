from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


COMPANY_RE = re.compile(r"^EMP_[A-Z0-9_]{2,40}$")
PROJECT_RE = re.compile(r"^PROY-\d{3}$")
MODULE_RE = re.compile(r"^[a-z][a-z0-9_]{1,60}$")
SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]{1,60}$")
PLATFORMS = {"render", "vercel", "streamlit", "local", "telegram", "internal"}


class FactoryProjectScaffoldService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip().upper()
        project_code = str(context.get("project_code") or "").strip().upper()
        module_code = str(context.get("module_code") or "").strip().lower()
        schema = str(context.get("schema") or context.get("supabase_schema") or "").strip().lower()
        project_name = str(context.get("project_name") or module_code or project_code).strip()
        platform = str(context.get("platform") or "render").strip().lower()
        requires_env = self._requires_env(context)
        dry_run = context.get("dry_run", True)
        overwrite = bool(context.get("overwrite", False))

        errors = self._validate(company_id, project_code, module_code, schema, platform, requires_env)
        if errors:
            return {"ok": False, "error": "; ".join(errors)}

        repo_root = Path(__file__).resolve().parents[5]
        company_dir = repo_root / "companies" / company_id
        company_config = company_dir / "company.json"
        if not company_config.exists():
            return {"ok": False, "error": "company.json no existe para la empresa solicitada; usa company_scaffold primero"}

        projects_dir = company_dir / "projects"
        existing = sorted(path for path in projects_dir.glob(f"{project_code}*") if path.is_dir()) if projects_dir.exists() else []
        if existing and not overwrite:
            return {
                "ok": False,
                "error": "project_code ya existe en esta empresa",
                "data": {"existing": [self._rel(path, repo_root) for path in existing]},
            }

        project_dir = projects_dir / f"{project_code}_{module_code.upper()}"
        files = self._planned_files(project_dir, company_id, project_code, module_code, project_name, schema, platform, requires_env)
        planned = {self._rel(path, repo_root): content for path, content in files.items()}

        if dry_run:
            return {"ok": True, "message": "dry_run: no se crearon archivos", "data": {"files": list(planned.keys()), "preview": planned}}

        written = []
        skipped = []
        for path, content in files.items():
            if path.exists() and not overwrite:
                skipped.append(self._rel(path, repo_root))
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, dict):
                path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                path.write_text(str(content), encoding="utf-8")
            written.append(self._rel(path, repo_root))

        audit = None
        if context.get("run_audit", True):
            audit = self._run_audit(repo_root, project_dir)

        return {
            "ok": True,
            "data": {
                "company_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
                "schema": schema,
                "project_dir": self._rel(project_dir, repo_root),
                "written": written,
                "skipped": skipped,
                "audit": audit,
            },
        }

    def _planned_files(
        self,
        project_dir: Path,
        company_id: str,
        project_code: str,
        module_code: str,
        project_name: str,
        schema: str,
        platform: str,
        requires_env: list[str],
    ) -> dict[Path, dict | str]:
        return {
            project_dir / "project.json": {
                "company_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
                "project_name": project_name,
                "schema": schema,
                "supabase_schema": schema,
                "platform": platform,
                "requires_env": requires_env,
                "status": "planned",
                "erp_ready": False,
            },
            project_dir / "AGENTS_ARCHITECTURE.md": self._architecture_md(company_id, project_code, module_code, schema),
            project_dir / ".env.example": "\n".join(f"{key}=" for key in requires_env) + "\n",
        }

    def _validate(self, company_id: str, project_code: str, module_code: str, schema: str, platform: str, requires_env: list[str]) -> list[str]:
        errors = []
        if not COMPANY_RE.match(company_id):
            errors.append("company_id debe usar patron de empresa Factory")
        if not PROJECT_RE.match(project_code):
            errors.append("project_code debe usar patron de proyecto Factory")
        if not MODULE_RE.match(module_code):
            errors.append("module_code invalido")
        if not SCHEMA_RE.match(schema):
            errors.append("schema invalido")
        if platform not in PLATFORMS:
            errors.append("platform invalido")
        if not all(isinstance(key, str) and key.strip() for key in requires_env):
            errors.append("requires_env debe ser lista de strings")
        return errors

    def _requires_env(self, context: dict) -> list[str]:
        raw = context.get("requires_env")
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        return ["SUPABASE_URL"]

    def _architecture_md(self, company_id: str, project_code: str, module_code: str, schema: str) -> str:
        return (
            "# Arquitectura del proyecto\n\n"
            f"- company_id: `{company_id}`\n"
            f"- project_code: `{project_code}`\n"
            f"- module_code: `{module_code}`\n"
            f"- schema: `{schema}`\n\n"
            "Reglas:\n"
            "- Todo codigo reusable recibe identidad por context/config.\n"
            "- No hardcodear empresa, schema, project_code, URLs ni tokens.\n"
            "- Antes de cierre correr `factory_no_hardcode_audit`.\n"
        )

    def _run_audit(self, repo_root: Path, project_dir: Path) -> dict | None:
        skill_file = repo_root / "factory" / "skills" / "internos" / "vertical_factory_utils" / "factory_no_hardcode_audit" / "skill.py"
        if not skill_file.exists():
            return {"ok": False, "error": "factory_no_hardcode_audit no encontrado"}
        spec = importlib.util.spec_from_file_location("_factory_no_hardcode_audit_skill", skill_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "no se pudo cargar factory_no_hardcode_audit"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.run({"paths": [self._rel(project_dir, repo_root)], "include_allowed": False})
        data = result.get("data") if isinstance(result, dict) else None
        return {
            "ok": bool(result.get("ok")) if isinstance(result, dict) else False,
            "summary": data.get("summary") if isinstance(data, dict) else None,
        }

    def _rel(self, path: Path, repo_root: Path) -> str:
        try:
            return str(path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            return str(path)
