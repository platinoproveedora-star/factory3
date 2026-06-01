from __future__ import annotations

from datetime import datetime, timezone


MODULE_ORDER = {
    "gastos": 10,
    "ventas": 20,
    "inventario": 30,
    "compras": 40,
    "crm": 50,
    "cxc": 60,
    "cxp": 70,
    "erp_core": 90,
}

VALID_STATUSES = {"planned", "in_progress", "active", "ready", "blocked", "closed", "legacy"}


class ErpModuleRegistryService:
    def ejecutar(self, context: dict) -> dict:
        company_id = self._company_id(context)
        modules = self._normalize_modules(context.get("modules") or [])
        issues: list[str] = []
        warnings: list[str] = []

        if not company_id:
            issues.append("company_id/empresa_id requerido")
        if not modules:
            issues.append("modules requerido")

        seen_codes: set[str] = set()
        seen_projects: set[str] = set()
        for module in modules:
            self._validate_module(module, seen_codes, seen_projects, issues, warnings)

        modules.sort(key=lambda item: (MODULE_ORDER.get(item["module_code"], 500), item["project_code"]))
        summary = self._summary(modules)

        registry = {
            "company_id": company_id,
            "empresa_id": company_id,
            "version": str(context.get("version") or "0.1.0"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "modules": modules,
            "summary": summary,
        }

        return {
            "ok": not issues,
            "data": {
                "registry": registry,
                "issues": issues,
                "warnings": warnings,
                "ready": not issues,
            },
        }

    def _company_id(self, context: dict) -> str:
        return str(context.get("company_id") or context.get("empresa_id") or "").strip()

    def _normalize_modules(self, raw_modules) -> list[dict]:
        if isinstance(raw_modules, dict):
            iterable = raw_modules.values()
        elif isinstance(raw_modules, list):
            iterable = raw_modules
        else:
            iterable = []

        modules = []
        for raw in iterable:
            if not isinstance(raw, dict):
                continue
            project_code = str(raw.get("project_code") or raw.get("code") or "").strip()
            module_code = str(raw.get("module_code") or raw.get("module") or "").strip()
            status = str(raw.get("status") or "planned").strip()
            modules.append({
                "project_code": project_code,
                "module_code": module_code,
                "project_name": str(raw.get("project_name") or raw.get("name") or "").strip(),
                "status": status,
                "erp_ready": bool(raw.get("erp_ready", False)),
                "schema": str(raw.get("schema") or raw.get("supabase_schema") or "").strip() or None,
                "folder": str(raw.get("folder") or "").strip() or None,
                "dashboard_url": str(raw.get("dashboard_url") or "").strip() or None,
                "depends_on": list(raw.get("depends_on") or []),
                "notes": str(raw.get("notes") or "").strip() or None,
            })
        return modules

    def _validate_module(
        self,
        module: dict,
        seen_codes: set[str],
        seen_projects: set[str],
        issues: list[str],
        warnings: list[str],
    ) -> None:
        project_code = module.get("project_code") or ""
        module_code = module.get("module_code") or ""
        status = module.get("status") or ""

        if not project_code:
            issues.append("modulo sin project_code")
        elif project_code in seen_projects:
            issues.append(f"project_code duplicado: {project_code}")
        seen_projects.add(project_code)

        if not module_code:
            issues.append(f"{project_code or '?'}: module_code requerido")
        elif module_code in seen_codes:
            warnings.append(f"module_code duplicado: {module_code}")
        seen_codes.add(module_code)

        if status not in VALID_STATUSES:
            warnings.append(f"{project_code or module_code}: status no estandar: {status}")
        if module_code != "erp_core" and not module.get("schema"):
            warnings.append(f"{project_code or module_code}: schema faltante")
        if module.get("erp_ready") and status not in {"active", "ready", "closed"}:
            warnings.append(f"{project_code or module_code}: erp_ready true con status {status}")

    def _summary(self, modules: list[dict]) -> dict:
        by_status: dict[str, int] = {}
        for module in modules:
            status = module.get("status") or "planned"
            by_status[status] = by_status.get(status, 0) + 1
        return {
            "total": len(modules),
            "erp_ready": sum(1 for module in modules if module.get("erp_ready")),
            "by_status": by_status,
            "module_codes": [module["module_code"] for module in modules],
        }

