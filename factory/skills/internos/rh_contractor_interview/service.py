"""Service for rh_contractor_interview — cuestionario de entrevista ajustado al contratista."""

from __future__ import annotations
import json
import os


class RhContractorInterviewService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        puesto         = context["puesto"]
        contratista    = context["contratista"]
        requisitos     = context.get("requisitos", [])
        equipo         = context.get("equipo", [])
        zona           = context.get("zona", "")
        profundidad    = context.get("profundidad", "media")
        canal          = context.get("canal", "telegram")
        num_preguntas  = int(context.get("num_preguntas", 8))
        vacante_id     = context.get("vacante_id", "")
        guardar        = context.get("guardar", False)

        preguntas = self._generar(puesto, contratista, requisitos, equipo, zona, profundidad, canal, num_preguntas)
        if not preguntas["ok"]:
            return preguntas

        if guardar and vacante_id:
            self._guardar(vacante_id, contratista, preguntas["data"]["preguntas"])

        return preguntas

    def _generar(self, puesto, contratista, requisitos, equipo, zona, profundidad, canal, num_preguntas) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

        req_str   = ", ".join(requisitos) if requisitos else "no especificados"
        equip_str = ", ".join(equipo) if equipo else "no especificado"

        instruccion_canal = (
            "Preguntas cortas, directas, adecuadas para responder por mensaje de texto en Telegram/WhatsApp."
            if canal in ("telegram", "whatsapp")
            else "Preguntas claras para entrevista presencial o videollamada."
        )

        niveles = {
            "simple": "preguntas básicas de filtro rápido",
            "media":  "preguntas equilibradas entre filtro y profundidad técnica",
            "robusto":"preguntas detalladas con escenarios situacionales",
        }
        nivel_desc = niveles.get(profundidad, niveles["media"])

        prompt = (
            f"Genera un cuestionario de entrevista para el contratista '{contratista}'.\n\n"
            f"Puesto: {puesto}\n"
            f"Zona: {zona or 'no especificada'}\n"
            f"Requisitos específicos del contratista: {req_str}\n"
            f"Equipo/vehículos que opera: {equip_str}\n"
            f"Profundidad: {nivel_desc}\n"
            f"Canal: {instruccion_canal}\n"
            f"Número de preguntas: {num_preguntas}\n\n"
            f"Incluye preguntas sobre:\n"
            f"1. Experiencia específica con el equipo del contratista\n"
            f"2. Disponibilidad y condiciones de trabajo\n"
            f"3. Situaciones específicas de esa empresa o industria\n"
            f"4. Al menos 1 pregunta de verificación de veracidad\n\n"
            f"Devuelve ÚNICAMENTE un JSON:\n"
            f'{{"preguntas": [{{"orden": 1, "pregunta": "...", "dimension": "..."}}]}}'
        )

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return {
                "ok": True,
                "data": {
                    "puesto":      puesto,
                    "contratista": contratista,
                    "canal":       canal,
                    "profundidad": profundidad,
                    "preguntas":   data.get("preguntas", []),
                },
            }
        except json.JSONDecodeError:
            return {"ok": False, "error": f"respuesta IA no es JSON válido: {raw[:200]}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _guardar(self, vacante_id: str, contratista: str, preguntas: list) -> None:
        try:
            from factory.engine import SupabaseClient
            sb = SupabaseClient({})
            sb.rest_upsert("cuestionarios", {
                "vacante_id":  vacante_id,
                "empresa_id":  contratista,
                "puesto":      "",
                "profundidad": "custom",
                "canal":       "telegram",
                "preguntas":   preguntas,
            })
        except Exception:
            pass

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("puesto"):
            return False, "puesto es requerido"
        if not context.get("contratista"):
            return False, "contratista es requerido"
        return True, None
