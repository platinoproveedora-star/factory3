"""Bloquea gasto excesivo, campañas sin tracking o configuraciones riesgosas. Reglas fijas."""
from __future__ import annotations

_DEFAULTS = {
    "ctr_minimo":          0.5,
    "frecuencia_maxima":   5.0,
    "cpc_maximo_pct_alza": 300,
    "roas_minimo":         1.0,
    "dias_sin_conversion": 7,
}


class AdsGuardrailsService:

    def ejecutar(self, context: dict) -> dict:
        campana              = context.get("campana", "").strip()
        presupuesto_diario   = float(context.get("presupuesto_diario", 0))
        presupuesto_gastado  = float(context.get("presupuesto_gastado", 0))
        presupuesto_total    = float(context.get("presupuesto_total", 0))
        tiene_pixel          = bool(context.get("tiene_pixel", False))
        tiene_tracking       = bool(context.get("tiene_tracking", False))
        ctr                  = float(context.get("ctr", 0))
        roas                 = float(context.get("roas", 0))
        frecuencia           = float(context.get("frecuencia", 0))
        dias_sin_conversion  = int(context.get("dias_sin_conversion", 0))
        umbral_gasto_pct     = float(context.get("umbral_gasto_pct", 90))

        if not campana:
            return {"ok": False, "error": "campana requerido"}

        bloqueos     = []
        advertencias = []
        score_riesgo = 0

        if not tiene_pixel:
            bloqueos.append("Sin Pixel instalado — no es posible optimizar ni medir conversiones")
            score_riesgo += 40

        if not tiene_tracking:
            bloqueos.append("Sin UTMs ni tracking — no se puede atribuir resultados")
            score_riesgo += 20

        if presupuesto_total > 0:
            pct_gastado = (presupuesto_gastado / presupuesto_total) * 100
            if pct_gastado >= umbral_gasto_pct:
                bloqueos.append(f"Gasto {pct_gastado:.1f}% del total — límite de {umbral_gasto_pct}% alcanzado")
                score_riesgo += 30

        if ctr > 0 and ctr < _DEFAULTS["ctr_minimo"]:
            advertencias.append(f"CTR {ctr}% por debajo del mínimo recomendado {_DEFAULTS['ctr_minimo']}%")
            score_riesgo += 10

        if frecuencia > _DEFAULTS["frecuencia_maxima"]:
            advertencias.append(f"Frecuencia {frecuencia} supera máximo {_DEFAULTS['frecuencia_maxima']} — riesgo de fatiga")
            score_riesgo += 15

        if roas > 0 and roas < _DEFAULTS["roas_minimo"]:
            bloqueos.append(f"ROAS {roas} menor a {_DEFAULTS['roas_minimo']} — campaña no es rentable")
            score_riesgo += 25

        if dias_sin_conversion >= _DEFAULTS["dias_sin_conversion"]:
            advertencias.append(f"{dias_sin_conversion} días sin conversión — revisar audiencia y oferta")
            score_riesgo += 10

        aprobado = len(bloqueos) == 0
        score_riesgo = min(score_riesgo, 100)
        nivel = "critico" if score_riesgo >= 70 else "alto" if score_riesgo >= 40 else "medio" if score_riesgo >= 20 else "bajo"

        return {"ok": True, "data": {
            "aprobado":     aprobado,
            "campana":      campana,
            "score_riesgo": score_riesgo,
            "nivel_riesgo": nivel,
            "bloqueos":     bloqueos,
            "advertencias": advertencias,
            "accion":       "BLOQUEADO" if not aprobado else "APROBADO con advertencias" if advertencias else "APROBADO",
        }}
