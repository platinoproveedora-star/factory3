from __future__ import annotations


class DashboardKpiDesignerService:
    def ejecutar(self, context: dict) -> dict:
        domain = (context.get("domain") or context.get("type") or "").lower()
        if "expense" in domain or "gasto" in domain or context.get("schema") == "uc101_proy001":
            return {"ok": True, "data": self._expense_kpis()}
        source = context.get("primary_source", "main")
        return {
            "ok": True,
            "data": {
                "kpis": [
                    {"id": "total_records", "label": "Registros", "source": source, "calculation": "count(*)", "format": "number"},
                    {"id": "recent_records", "label": "Recientes", "source": source, "calculation": "count(last_30_days)", "format": "number"},
                ],
                "filters": [{"id": "search", "label": "Buscar", "field": "*", "type": "search"}],
                "groupings": [],
            },
        }

    def _expense_kpis(self) -> dict:
        return {
            "kpis": [
                {"id": "total_spend", "label": "Gasto total", "source": "gastos", "calculation": "sum(monto)", "format": "currency"},
                {"id": "expense_count", "label": "Movimientos", "source": "gastos", "calculation": "count(*)", "format": "number"},
                {"id": "avg_expense", "label": "Promedio por gasto", "source": "gastos", "calculation": "avg(monto)", "format": "currency"},
                {"id": "top_category", "label": "Categoria principal", "source": "gastos", "calculation": "max_group_by(categoria_id, sum(monto))", "format": "text"},
            ],
            "filters": [
                {"id": "date_range", "label": "Fecha", "field": "fecha", "type": "date_range"},
                {"id": "category", "label": "Categoria", "field": "categoria_id", "type": "select"},
                {"id": "search", "label": "Buscar concepto", "field": "descripcion", "type": "search"},
            ],
            "groupings": [
                {"id": "by_category", "label": "Por categoria", "field": "categoria_id", "metric": "sum(monto)"},
                {"id": "by_day", "label": "Por dia", "field": "fecha", "metric": "sum(monto)"},
                {"id": "by_capture_method", "label": "Por metodo de captura", "field": "metodo_captura", "metric": "count(*)"},
            ],
        }

