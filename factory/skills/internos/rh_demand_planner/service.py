"""Service for rh_demand_planner — calcula cuántos operadores contratar."""

from __future__ import annotations
import math
from datetime import date


class RhDemandPlannerService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        puesto = context["puesto"]
        zona = context.get("zona", "general")
        fecha_objetivo = context.get("fecha_objetivo", "")
        activos_actuales = int(context.get("activos_actuales", 0))
        demanda_total = int(context["demanda_total"])
        tasa_desercion = float(context.get("tasa_desercion", 0.20))
        dias_proceso = int(context.get("dias_proceso", 14))

        faltantes = max(0, demanda_total - activos_actuales)
        ajuste_desercion = math.ceil(faltantes * (1 + tasa_desercion))
        candidatos_necesarios = math.ceil(ajuste_desercion * 3)

        return {
            "ok": True,
            "data": {
                "puesto": puesto,
                "zona": zona,
                "fecha_objetivo": fecha_objetivo,
                "activos_actuales": activos_actuales,
                "demanda_total": demanda_total,
                "faltantes": faltantes,
                "a_contratar": ajuste_desercion,
                "candidatos_a_capturar": candidatos_necesarios,
                "dias_proceso": dias_proceso,
                "tasa_desercion_aplicada": tasa_desercion,
                "nota": f"Se necesitan ~{candidatos_necesarios} candidatos en pipeline para cubrir {ajuste_desercion} contrataciones.",
            },
        }

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("puesto"):
            return False, "puesto es requerido"
        if "demanda_total" not in context:
            return False, "demanda_total es requerido"
        try:
            int(context["demanda_total"])
        except (ValueError, TypeError):
            return False, "demanda_total debe ser entero"
        return True, None
