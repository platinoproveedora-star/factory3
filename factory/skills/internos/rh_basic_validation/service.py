"""Service for rh_basic_validation - validates minimum required candidate data."""

from __future__ import annotations


class RhBasicValidationService:

    def ejecutar(self, context: dict) -> dict:
        perfil = context.get("perfil")
        if not perfil or not isinstance(perfil, dict):
            return {"ok": False, "error": "perfil es requerido y debe ser un diccionario"}

        errores = []

        if not perfil.get("nombre", "").strip():
            errores.append("nombre")

        tiene_contacto = bool(perfil.get("telefono", "").strip() or perfil.get("email", "").strip())
        if not tiene_contacto:
            errores.append("contacto (telefono o email)")

        if not perfil.get("disponibilidad", "").strip():
            errores.append("disponibilidad")

        valido = len(errores) == 0

        return {
            "ok": True,
            "data": {
                "valido": valido,
                "campos_faltantes": errores,
                "message": "perfil valido" if valido else f"campos faltantes: {', '.join(errores)}",
            },
        }
