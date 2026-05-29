from __future__ import annotations

import re


class DashboardModulePlannerService:
    def ejecutar(self, context: dict) -> dict:
        req = context.get("requirements", {})
        project = req.get("project", {}) if isinstance(req, dict) else {}
        project = {
            "client_id": context.get("client_id") or project.get("client_id", ""),
            "project_code": context.get("project_code") or project.get("project_code", ""),
            "name": context.get("name") or project.get("name", "Dashboard operativo"),
            "slug": context.get("slug") or project.get("slug") or self._slug(context.get("name") or project.get("name", "dashboard")),
            "audience": project.get("audience", context.get("audience", [])),
            "business_goal": project.get("business_goal", context.get("business_goal", "")),
        }
        data_sources = context.get("data_sources") or []
        kpis = context.get("kpis") or []
        filters = context.get("filters") or []
        plan = {
            "version": "0.1.0",
            "project": project,
            "data_sources": data_sources,
            "kpis": kpis,
            "filters": filters,
            "pages": context.get("pages") or self._default_pages(kpis),
            "actions": context.get("actions") or [
                {"id": "export_csv", "label": "Exportar CSV", "type": "export", "format": "csv"},
            ],
        }
        return {"ok": True, "data": {"dashboard_plan": plan}}

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "dashboard"

    def _default_pages(self, kpis: list[dict]) -> list[dict]:
        return [
            {
                "id": "overview",
                "title": "Overview",
                "modules": [
                    {"id": "kpi_grid", "type": "kpi_grid", "title": "Indicadores", "source": "gastos", "config": {"kpis": [k.get("id") for k in kpis]}},
                    {"id": "spend_by_category", "type": "chart", "title": "Gasto por categoria", "source": "gastos", "config": {"chart": "bar", "group_by": "categoria_id", "metric": "sum(monto)"}},
                    {"id": "spend_by_day", "type": "chart", "title": "Gasto por dia", "source": "gastos", "config": {"chart": "line", "group_by": "fecha", "metric": "sum(monto)"}},
                    {"id": "expense_table", "type": "table", "title": "Detalle de gastos", "source": "gastos", "config": {"search": True, "export": True}},
                ],
            }
        ]

