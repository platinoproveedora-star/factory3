"""Service for rh_knockout_filter - hard pass/fail filter, no partial scores."""

from __future__ import annotations


class RhKnockoutFilterService:

    def ejecutar(self, context: dict) -> dict:
        perfil = context.get("perfil")
        reglas = context.get("reglas_knockout") or context.get("reglas", [])

        if not perfil or not isinstance(perfil, dict):
            return {"ok": False, "error": "perfil es requerido y debe ser un diccionario"}
        if not isinstance(reglas, list):
            return {"ok": False, "error": "reglas_knockout debe ser una lista"}
        if not reglas:
            return {
                "ok": True,
                "data": {"pasa": True, "razones_rechazo": [], "reglas_aplicadas": 0},
            }

        razones = []
        for regla in reglas:
            if not isinstance(regla, dict):
                continue
            campo = regla.get("campo", "")
            valor_campo = str(perfil.get(campo, "")).lower().strip()

            if "debe_contener" in regla:
                esperado = str(regla["debe_contener"]).lower().strip()
                if esperado not in valor_campo:
                    razones.append(self._razon(campo, regla, valor_campo))

            elif "debe_ser_uno_de" in regla:
                opciones = [str(o).lower().strip() for o in regla["debe_ser_uno_de"]]
                if not any(op in valor_campo for op in opciones):
                    razones.append(self._razon(campo, regla, valor_campo))

            elif "no_debe_contener" in regla:
                prohibido = str(regla["no_debe_contener"]).lower().strip()
                if prohibido in valor_campo:
                    razones.append(self._razon(campo, regla, valor_campo))

            elif "debe_existir" in regla and regla["debe_existir"]:
                if not valor_campo:
                    razones.append(f"{campo}: campo requerido no presente")

        return {
            "ok": True,
            "data": {
                "pasa": len(razones) == 0,
                "razones_rechazo": razones,
                "reglas_aplicadas": len(reglas),
            },
        }

    def _razon(self, campo: str, regla: dict, valor_actual: str) -> str:
        if "debe_contener" in regla:
            return f"{campo}: se requiere '{regla['debe_contener']}', valor actual: '{valor_actual}'"
        if "debe_ser_uno_de" in regla:
            return f"{campo}: debe ser uno de {regla['debe_ser_uno_de']}, valor actual: '{valor_actual}'"
        if "no_debe_contener" in regla:
            return f"{campo}: no debe contener '{regla['no_debe_contener']}', valor actual: '{valor_actual}'"
        return f"{campo}: no cumple regla"
