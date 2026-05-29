from __future__ import annotations


class DashboardUpdatePlannerService:
    def ejecutar(self, context: dict) -> dict:
        changes = context.get("requested_changes") or context.get("changes") or ""
        if isinstance(changes, str):
            change_items = [c.strip() for c in changes.replace(";", "\n").splitlines() if c.strip()]
        else:
            change_items = changes if isinstance(changes, list) else []
        plan = {
            "update_type": self._classify(change_items),
            "changes": change_items,
            "affected_modules": self._affected(change_items),
            "steps": [
                "Actualizar dashboard_plan",
                "Regenerar modulos afectados",
                "Ejecutar quality_check",
                "Disparar deploy preview",
            ],
        }
        return {"ok": True, "data": {"update_plan": plan}}

    def _classify(self, changes: list[str]) -> str:
        text = " ".join(changes).lower()
        if any(word in text for word in ["nuevo modulo", "agrega", "grafica", "tabla"]):
            return "module_change"
        if any(word in text for word in ["color", "diseno", "layout"]):
            return "visual_change"
        if any(word in text for word in ["dato", "tabla", "campo", "supabase"]):
            return "data_change"
        return "minor_change"

    def _affected(self, changes: list[str]) -> list[str]:
        text = " ".join(changes).lower()
        affected = []
        if "tabla" in text:
            affected.append("tables")
        if "graf" in text or "chart" in text:
            affected.append("charts")
        if "kpi" in text or "indicador" in text:
            affected.append("kpis")
        return affected or ["dashboard_plan"]

