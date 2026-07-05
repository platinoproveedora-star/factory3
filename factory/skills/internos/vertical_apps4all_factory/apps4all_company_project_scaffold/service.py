from __future__ import annotations

import re
from pathlib import Path


COMPANY_RE = re.compile(r"^EMP_[A-Z0-9_]+$")
MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class Apps4AllCompanyProjectScaffoldService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip().upper()
        project_code = str(context.get("project_code") or "PROY-001").strip()
        module_code = str(context.get("module_code") or "").strip()
        schema = str(context.get("schema") or "").strip()
        company_name = str(context.get("company_name") or company_id).strip()

        errors = []
        if not COMPANY_RE.match(company_id):
            errors.append("company_id requerido con formato EMP_...")
        if not project_code:
            errors.append("project_code requerido")
        if not MODULE_RE.match(module_code):
            errors.append("module_code requerido snake_case")
        if not schema:
            errors.append("schema requerido")
        if errors:
            return {"ok": False, "error": "; ".join(errors)}

        project_path = Path("companies") / company_id / "projects" / f"{project_code}_{module_code.upper()}"
        plan = {
            "company_json": {"company_id": company_id, "name": company_name, "status": "active"},
            "project_json": {
                "company_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
                "schema": schema,
                "platform": context.get("platform") or "vercel",
                "requires_env": context.get("requires_env") or [],
            },
            "project_path": str(project_path).replace("\\", "/"),
            "delegates": ["apps4all_company_scaffold", "apps4all_project_scaffold"],
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": plan}
        return {"ok": False, "error": "write real no implementado en este alias; usar delegates con autorizacion humana"}
