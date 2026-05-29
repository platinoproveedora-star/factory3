from __future__ import annotations

import re


class DashboardRequirementsAnalyzerService:
    def ejecutar(self, context: dict) -> dict:
        name = context.get("name") or context.get("project_name") or "Dashboard operativo"
        goal = context.get("business_goal") or context.get("objective") or "Analizar informacion operativa del negocio."
        audience = context.get("audience") or ["dueno", "administracion", "operacion"]
        if isinstance(audience, str):
            audience = [a.strip() for a in audience.split(",") if a.strip()]
        slug = context.get("slug") or self._slug(name)
        requirements = {
            "project": {
                "client_id": context.get("client_id", ""),
                "project_code": context.get("project_code", ""),
                "name": name,
                "slug": slug,
                "business_goal": goal,
                "audience": audience,
            },
            "users": [{"role": role, "needs": self._needs_for(role)} for role in audience],
            "must_have": context.get("must_have") or [
                "KPIs principales visibles al abrir",
                "filtros por fecha y categoria",
                "tabla auditable",
                "exportacion CSV/Excel",
            ],
            "nice_to_have": context.get("nice_to_have") or [
                "graficas por periodo",
                "vista movil",
                "control de acceso",
            ],
            "constraints": context.get("constraints") or [
                "No depender de Streamlit para entrega final",
                "Consumir datos desde Supabase o Factory3 data skills",
            ],
        }
        return {"ok": True, "data": {"requirements": requirements}}

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "dashboard"

    def _needs_for(self, role: str) -> list[str]:
        low = role.lower()
        if "admin" in low or "dueno" in low or "owner" in low:
            return ["ver totales", "detectar desviaciones", "exportar datos"]
        if "oper" in low:
            return ["revisar movimientos", "filtrar rapido", "capturar correcciones"]
        return ["consultar informacion clara", "filtrar", "descargar datos"]

