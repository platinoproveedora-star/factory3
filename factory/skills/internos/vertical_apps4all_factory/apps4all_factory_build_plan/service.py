from __future__ import annotations

import re
from pathlib import Path


COMPANY_RE = re.compile(r"^EMP_[A-Z0-9_]+$")
MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class Apps4AllFactoryBuildPlanService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip().upper()
        project_code = str(context.get("project_code") or "PROY-001").strip()
        module_code = str(context.get("module_code") or "").strip()
        schema = str(context.get("schema") or "").strip()
        project_path = str(context.get("project_path") or self._default_project_path(company_id, project_code, module_code)).replace("\\", "/")
        source_project_path = str(context.get("source_project_path") or "").strip().replace("\\", "/")

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

        mode = "clone" if source_project_path else "new"
        steps = [
            self._step("context", "resolver company/project/module/schema", {"company_id": company_id, "project_code": project_code, "module_code": module_code, "schema": schema}),
            self._step("company_project", "crear o validar company.json/project.json", {"skill": "vertical_apps4all_factory/apps4all_company_project_scaffold"}),
            self._step("auth_bridge", "crear o validar SSO Apps4All + login directo", {"skill": "vertical_apps4all_auth_bridge/apps4all_auth_bridge_plan", "project_path": project_path, "module_code": module_code}),
            self._step("dashboard", "crear o validar dashboard Apps4All-compatible", {"skill": "vertical_apps4all_dash/apps4all_dash_scaffold", "project_path": project_path}),
            self._step("marketplace", "registrar modulo vendible", {"skill": "vertical_apps4all_marketplace/apps4all_marketplace_module_register", "module_code": module_code}),
            self._step("demo_seed", "crear empresa/usuario/grants demo si aplica", {"skill": "vertical_apps4all_productization/apps4all_demo_seed", "module_code": module_code}),
            self._step("publish_check", "auditar cierre vendible", {"skill": "vertical_apps4all_productization/apps4all_publish_check", "project_path": project_path}),
            self._step("billing", "planear billing Stripe Apps4All", {"skill": "vertical_apps4all_billing_stripe/apps4all_billing_plan", "module_code": module_code}),
            self._step("release", "planear Vercel y URL Marketplace", {"skill": "vertical_apps4all_release/apps4all_release_plan", "project_path": project_path}),
            self._step("remote_smoke", "planear smoke remoto post-release", {"skill": "vertical_apps4all_remote_smoke_suite/apps4all_remote_smoke_plan", "module_code": module_code}),
            self._step("ops_monitoring", "planear monitoreo operativo", {"skill": "vertical_apps4all_ops_monitoring/apps4all_ops_monitoring_plan", "module_code": module_code, "project_path": project_path}),
        ]
        if mode == "clone":
            steps.insert(2, self._step("clone", "clonar modulo existente a empresa destino", {"skill": "vertical_apps4all_module_clone/apps4all_module_clone_execute", "source_project_path": source_project_path, "target_project_path": project_path}))

        return {
            "ok": True,
            "data": {
                "mode": mode,
                "company_id": company_id,
                "project_code": project_code,
                "module_code": module_code,
                "schema": schema,
                "project_path": project_path,
                "source_project_path": source_project_path or None,
                "steps": steps,
                "default_policy": {"dry_run": True, "requires_human_confirmation_for_writes": True},
            },
        }

    def _default_project_path(self, company_id: str, project_code: str, module_code: str) -> Path:
        return Path("companies") / company_id / "projects" / f"{project_code}_{module_code.upper()}"

    def _step(self, name: str, description: str, context: dict) -> dict:
        return {"name": name, "description": description, "context": context}
