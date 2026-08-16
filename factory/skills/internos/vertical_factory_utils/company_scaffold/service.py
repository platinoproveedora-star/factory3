from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


COMPANY_RE = re.compile(r"^EMP_[A-Z0-9_]{2,40}$")
PROJECT_RE = re.compile(r"^PROY-\d{3}$")
MODULE_RE = re.compile(r"^[a-z][a-z0-9_]{1,60}$")
SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]{1,60}$")


class CompanyScaffoldService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip().upper()
        project_code = str(context.get("project_code") or "").strip().upper()
        module_code = str(context.get("module_code") or "").strip().lower()
        schema = str(context.get("schema") or context.get("supabase_schema") or "").strip().lower()
        project_name = str(context.get("project_name") or module_code or project_code).strip()
        platform = str(context.get("platform") or "render").strip().lower()
        requires_env = context.get("requires_env") if isinstance(context.get("requires_env"), list) else ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        dry_run = context.get("dry_run", True)

        errors = self._validate(company_id, project_code, module_code, schema, platform)
        if errors:
            return {"ok": False, "error": "; ".join(errors)}

        repo_root = Path(__file__).resolve().parents[5]
        company_dir = repo_root / "companies" / company_id
        project_dir = company_dir / "projects" / f"{project_code}_{module_code.upper()}"

        files = {
            company_dir / "company.json": {
                "company_id": company_id,
                "status": "active",
                "projects_dir": f"companies/{company_id}/projects",
            },
            company_dir / "company.config.json": self._company_config(company_id, schema, context),
            company_dir / "README.md": self._readme_md(company_id, project_code, module_code, schema, platform, context),
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

        planned = {self._rel(path, repo_root): content for path, content in files.items()}
        if dry_run:
            return {"ok": True, "message": "dry_run: no se crearon archivos", "data": {"files": list(planned.keys()), "preview": planned}}

        written = []
        for path, content in files.items():
            if path.exists() and not context.get("overwrite", False):
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, dict):
                path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                path.write_text(str(content), encoding="utf-8")
            written.append(self._rel(path, repo_root))
        return {"ok": True, "data": {"company_id": company_id, "project_code": project_code, "module_code": module_code, "schema": schema, "written": written}}

    def _validate(self, company_id: str, project_code: str, module_code: str, schema: str, platform: str) -> list[str]:
        errors = []
        if not COMPANY_RE.match(company_id):
            errors.append("company_id debe usar patron de empresa Factory")
        if not PROJECT_RE.match(project_code):
            errors.append("project_code debe usar patron de proyecto Factory")
        if not MODULE_RE.match(module_code):
            errors.append("module_code invalido")
        if not SCHEMA_RE.match(schema):
            errors.append("schema invalido")
        if platform not in {"render", "vercel", "streamlit", "local", "telegram", "internal"}:
            errors.append("platform invalido")
        return errors

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

    def _company_config(self, company_id: str, schema: str, context: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        primary_contact = context.get("primary_contact")
        legacy_ids = context.get("legacy_ids")
        return {
            "company_id": company_id,
            "company_name": str(context.get("company_name") or "").strip(),
            "short_name": str(context.get("short_name") or "").strip(),
            "company_type": str(context.get("company_type") or "").strip(),
            "industry": str(context.get("industry") or "").strip(),
            "status": "active",
            "relationship": str(context.get("relationship") or "").strip(),
            "primary_contact": primary_contact if isinstance(primary_contact, dict) else {"name": "", "email": ""},
            "objective": str(context.get("objective") or "").strip(),
            "legacy_ids": legacy_ids if isinstance(legacy_ids, dict) else {},
            "dashboards": [],
            "skill_stack": [],
            "channels": [],
            "storage": {"supabase_schema": schema, "buckets": []},
            "default_authorizer": context.get("default_authorizer") or None,
            "created_at": now,
            "updated_at": now,
        }

    def _readme_md(self, company_id: str, project_code: str, module_code: str, schema: str, platform: str, context: dict) -> str:
        company_name = str(context.get("company_name") or "").strip()
        title_line = f"**{company_name}**\n\n" if company_name else ""
        return (
            f"# {company_id}\n\n"
            f"{title_line}"
            f"Empresa Factory3. Identidad principal: `{company_id}`.\n\n"
            "## Proyectos\n\n"
            "| Codigo | Modulo | Estado | Dashboard |\n"
            "|---|---|---|---|\n"
            f"| {project_code} | {module_code} | planned | - |\n\n"
            "## Infraestructura\n\n"
            "| Recurso | Valor |\n"
            "|---|---|\n"
            f"| Schema {module_code} | `{schema}` |\n"
            f"| Plataforma | {platform} |\n\n"
            "## Identidad ERP\n\n"
            "```text\n"
            f"empresa_id = {company_id}\n"
            f"company_id = {company_id}\n"
            f"{project_code} = {module_code}\n"
            "```\n\n"
            "Todo registro operativo lleva: `empresa_id` + `project_code` + `module_code` + `id uuid` + `folio text unique`.\n"
        )

    def _rel(self, path: Path, repo_root: Path) -> str:
        try:
            return str(path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            return str(path)
