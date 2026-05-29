from __future__ import annotations


class NextjsModuleUpdaterService:
    def ejecutar(self, context: dict) -> dict:
        update_plan = context.get("update_plan") or {}
        affected = update_plan.get("affected_modules") or ["dashboard_plan"]
        tasks = []
        for module in affected:
            if module == "charts":
                tasks.append({"skill": "vertical_nextjs/nextjs_chart_builder", "reason": "regenerar graficas"})
            elif module == "tables":
                tasks.append({"skill": "vertical_nextjs/nextjs_table_builder", "reason": "regenerar tablas"})
            elif module == "kpis":
                tasks.append({"skill": "vertical_nextjs/nextjs_module_generator", "reason": "actualizar tarjetas KPI"})
            else:
                tasks.append({"skill": "vertical_nextjs/nextjs_module_generator", "reason": "actualizar pagina principal"})
        return {"ok": True, "data": {"tasks": tasks, "manual_review_required": True}}

