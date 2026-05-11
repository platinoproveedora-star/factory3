"""Evalúa latencia de una tarea contra umbrales en ms."""
from __future__ import annotations

_UMBRAL_WARN = 5_000    # ms — advertencia
_UMBRAL_LENTO = 30_000  # ms — lento


class SkillLatencyEvalService:

    def ejecutar(self, context: dict) -> dict:
        latencia_ms  = int(context.get("latencia_ms", 0))
        umbral_warn  = int(context.get("umbral_warn",  _UMBRAL_WARN))
        umbral_lento = int(context.get("umbral_lento", _UMBRAL_LENTO))

        nivel = "normal"
        if latencia_ms >= umbral_lento:
            nivel = "lento"
        elif latencia_ms >= umbral_warn:
            nivel = "advertencia"

        return {
            "ok": True,
            "data": {
                "eval":       "latency",
                "latencia_ms": latencia_ms,
                "nivel":      nivel,
                "aprobado":   nivel != "lento",
            },
        }
