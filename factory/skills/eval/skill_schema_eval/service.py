"""Valida que data del resultado contenga los campos requeridos."""
from __future__ import annotations


class SkillSchemaEvalService:

    def ejecutar(self, context: dict) -> dict:
        resultado    = context.get("resultado")
        campos_req   = context.get("campos_requeridos", [])

        if resultado is None:
            return {"ok": False, "error": "resultado requerido"}
        if not campos_req:
            return {"ok": True, "data": {"eval": "schema", "aprobado": True, "faltantes": [], "score": 1.0}}

        data     = resultado.get("data", {}) if isinstance(resultado, dict) else {}
        faltantes = [c for c in campos_req if c not in data]
        aprobado  = len(faltantes) == 0
        score     = round(1.0 - len(faltantes) / len(campos_req), 2)

        return {
            "ok": True,
            "data": {
                "eval":      "schema",
                "aprobado":  aprobado,
                "faltantes": faltantes,
                "score":     score,
            },
        }
