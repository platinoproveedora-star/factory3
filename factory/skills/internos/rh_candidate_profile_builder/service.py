"""Service for rh_candidate_profile_builder - builds structured profile from questionnaire answers."""

from __future__ import annotations

import re

from factory.engine import SupabaseClient

_CAMPO_KEYWORDS = {
    "nombre":         ["nombre", "llamas", "apellido", "completo"],
    "telefono":       ["telefono", "celular", "numero", "movil", "whatsapp", "contacto"],
    "email":          ["email", "correo", "mail"],
    "ubicacion":      ["vives", "zona", "colonia", "ciudad", "ubicacion", "municipio", "estado"],
    "disponibilidad": ["disponibilidad", "horario", "turno", "dias", "lunes", "sabado", "semana"],
    "experiencia":    ["experiencia", "trabajado", "anterior", "previo", "anos", "tiempo"],
    "licencia":       ["licencia", "conducir", "manejar", "tipo"],
}

_TELEFONO_RE = re.compile(r"\b\d[\d\s\-().]{7,}\d\b")
_EMAIL_RE    = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


class RhCandidateProfileBuilderService:

    def ejecutar(self, context: dict) -> dict:
        candidato_id = context.get("candidato_id", "").strip()
        respuestas = context.get("respuestas")

        if not candidato_id:
            return {"ok": False, "error": "candidato_id es requerido"}

        db = SupabaseClient(context)

        if not respuestas:
            result = db.rest_select(
                "respuestas",
                filters={"candidato_id": candidato_id},
                select="pregunta,respuesta,orden",
                order="orden.asc",
            )
            if not result.get("ok"):
                return result
            respuestas = result.get("data") or []

        if not respuestas:
            return {"ok": False, "error": "no hay respuestas para construir el perfil"}

        perfil = self._extraer_perfil(respuestas)

        # Actualizar candidatos con campos extraidos
        campos_actualizar = {k: v for k, v in {
            "nombre":   perfil.get("nombre"),
            "telefono": perfil.get("telefono"),
            "email":    perfil.get("email"),
            "estado":   "capturando_datos",
        }.items() if v}

        if campos_actualizar:
            db.rest_update("candidatos", values=campos_actualizar, filters={"id": candidato_id})

        return {
            "ok": True,
            "message": "perfil construido",
            "data": {"candidato_id": candidato_id, "perfil": perfil},
        }

    def _extraer_perfil(self, respuestas: list) -> dict:
        perfil: dict = {}
        for item in respuestas:
            pregunta  = (item.get("pregunta") or "").lower()
            respuesta = (item.get("respuesta") or "").strip()
            if not respuesta:
                continue
            campo = self._detectar_campo(pregunta)
            if campo and campo not in perfil:
                valor = self._limpiar_valor(campo, respuesta)
                if valor:
                    perfil[campo] = valor
        # Extraccion por patron si no se capturo por keyword
        for item in respuestas:
            respuesta = (item.get("respuesta") or "").strip()
            if not respuesta:
                continue
            if "telefono" not in perfil:
                m = _TELEFONO_RE.search(respuesta)
                if m:
                    perfil["telefono"] = re.sub(r"[\s\-().]", "", m.group())
            if "email" not in perfil:
                m = _EMAIL_RE.search(respuesta)
                if m:
                    perfil["email"] = m.group().lower()
        return perfil

    def _detectar_campo(self, pregunta: str) -> str | None:
        for campo, keywords in _CAMPO_KEYWORDS.items():
            if any(kw in pregunta for kw in keywords):
                return campo
        return None

    def _limpiar_valor(self, campo: str, valor: str) -> str:
        if campo == "telefono":
            limpio = re.sub(r"[\s\-().]", "", valor)
            return limpio if re.fullmatch(r"\+?\d{8,15}", limpio) else valor
        if campo == "email":
            m = _EMAIL_RE.search(valor)
            return m.group().lower() if m else valor
        return valor
