"""Valida que el resultado de un skill cumpla el contrato estándar."""
from __future__ import annotations


class SkillInputOutputEvalService:

    def ejecutar(self, context: dict) -> dict:
        resultado = context.get("resultado")
        if resultado is None:
            return {"ok": False, "error": "resultado requerido"}

        errores = []
        if not isinstance(resultado, dict):
            errores.append("resultado no es dict")
        else:
            if "ok" not in resultado:
                errores.append("falta campo 'ok'")
            elif not isinstance(resultado["ok"], bool):
                errores.append("'ok' debe ser bool")

            if resultado.get("ok") and "data" not in resultado:
                errores.append("ok=True pero falta 'data'")
            if not resultado.get("ok") and "error" not in resultado:
                errores.append("ok=False pero falta 'error'")

        aprobado = len(errores) == 0
        return {
            "ok": True,
            "data": {
                "eval":     "input_output",
                "aprobado": aprobado,
                "errores":  errores,
                "score":    1.0 if aprobado else 0.0,
            },
        }
