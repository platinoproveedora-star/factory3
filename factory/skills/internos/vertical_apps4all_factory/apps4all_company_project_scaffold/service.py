from __future__ import annotations

import re
from pathlib import Path

COMPANY_RE = re.compile(r"^EMP_[A-Z0-9_]+$")
MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class Apps4AllCompanyProjectScaffoldService:
    """Crea una empresa+proyecto+dashboard Apps4All nuevos en un solo paso.

    Orquesta, en este orden, dos skills que ya existen y no se reimplementan:
    1. apps4all_dash_scaffold -> clona el dashboard base (Next.js/Vercel, auth
       Apps4All completo) al directorio del proyecto.
    2. vertical_factory_utils/company_scaffold -> completa company.json y
       AGENTS_ARCHITECTURE.md (no pisa project.json/.env.example que ya dejo
       el dashboard, que son mas completos).
    """

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip().upper()
        project_code = str(context.get("project_code") or "PROY-001").strip().upper()
        module_code = str(context.get("module_code") or "").strip().lower()
        schema = str(context.get("schema") or context.get("supabase_schema") or "").strip().lower()
        dashboard_name = str(context.get("dashboard_name") or context.get("project_name") or module_code).strip()
        template_path = context.get("template_path")
        dry_run = context.get("dry_run", True)

        errors = []
        if not COMPANY_RE.match(company_id):
            errors.append("company_id requerido con formato EMP_...")
        if not project_code:
            errors.append("project_code requerido")
        if not module_code or not MODULE_RE.match(module_code):
            errors.append("module_code invalido (snake_case)")
        if not schema or not MODULE_RE.match(schema):
            errors.append("schema invalido (snake_case)")
        if errors:
            return {"ok": False, "error": "; ".join(errors)}

        target_path = f"companies/{company_id}/projects/{project_code}_{module_code.upper()}"
        runner = _runner()

        dash_context = {
            "company_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
            "schema": schema,
            "dashboard_name": dashboard_name,
            "target_path": target_path,
            "dry_run": dry_run,
        }
        if template_path:
            dash_context["template_path"] = template_path
        dash_res = runner.run("vertical_apps4all_dash/apps4all_dash_scaffold", dash_context)
        if not dash_res.get("ok"):
            return {"ok": False, "error": "dash_scaffold_failed", "data": {"detail": dash_res.get("error")}}

        company_res = runner.run(
            "vertical_factory_utils/company_scaffold",
            {
                "company_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
                "project_name": dashboard_name,
                "schema": schema,
                "platform": "vercel",
                "requires_env": context.get("requires_env") or ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"],
                "dry_run": dry_run,
                "overwrite": False,
            },
        )
        if not company_res.get("ok"):
            return {
                "ok": False,
                "error": "company_scaffold_failed",
                "data": {"detail": company_res.get("error"), "dash_scaffold": dash_res.get("data")},
            }

        return {
            "ok": True,
            "data": {
                "company_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
                "schema": schema,
                "target_path": target_path,
                "dash_scaffold": dash_res.get("data"),
                "company_scaffold": company_res.get("data"),
            },
        }
