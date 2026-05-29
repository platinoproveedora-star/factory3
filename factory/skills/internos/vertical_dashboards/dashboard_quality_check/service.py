from __future__ import annotations


class DashboardQualityCheckService:
    def ejecutar(self, context: dict) -> dict:
        plan = context.get("dashboard_plan") or context.get("plan") or {}
        issues = []
        warnings = []
        if not plan.get("project", {}).get("name"):
            issues.append("project.name faltante")
        if not plan.get("data_sources"):
            issues.append("data_sources vacio")
        if not plan.get("kpis"):
            warnings.append("No hay KPIs definidos")
        if not plan.get("pages"):
            issues.append("pages vacio")
        for page in plan.get("pages", []):
            if not page.get("modules"):
                issues.append(f"page {page.get('id', '?')} sin modulos")
        has_table = any(m.get("type") == "table" for p in plan.get("pages", []) for m in p.get("modules", []))
        has_export = any((m.get("config") or {}).get("export") for p in plan.get("pages", []) for m in p.get("modules", []))
        if not has_table:
            warnings.append("No hay tabla auditable")
        if not has_export:
            warnings.append("No hay exportacion configurada")
        score = max(0, 100 - len(issues) * 25 - len(warnings) * 8)
        return {"ok": not issues, "data": {"score": score, "issues": issues, "warnings": warnings, "ready_for_build": not issues}}

