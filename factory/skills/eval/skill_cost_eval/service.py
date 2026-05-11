"""Evalúa costo en tokens contra umbrales."""
from __future__ import annotations

_UMBRAL_WARN  = 2000   # tokens — advertencia
_UMBRAL_ALTO  = 8000   # tokens — costo alto
_COSTO_HAIKU  = 0.0000008   # USD por token (input+output promedio)
_COSTO_SONNET = 0.000008


class SkillCostEvalService:

    def ejecutar(self, context: dict) -> dict:
        tokens       = int(context.get("costo_tokens", 0))
        umbral_warn  = int(context.get("umbral_warn",  _UMBRAL_WARN))
        umbral_alto  = int(context.get("umbral_alto",  _UMBRAL_ALTO))
        modelo       = context.get("modelo", "haiku")

        costo_usd = tokens * (_COSTO_SONNET if "sonnet" in modelo else _COSTO_HAIKU)
        nivel     = "normal"
        if tokens >= umbral_alto:
            nivel = "alto"
        elif tokens >= umbral_warn:
            nivel = "advertencia"

        return {
            "ok": True,
            "data": {
                "eval":       "cost",
                "tokens":     tokens,
                "costo_usd":  round(costo_usd, 6),
                "nivel":      nivel,
                "aprobado":   nivel != "alto",
            },
        }
