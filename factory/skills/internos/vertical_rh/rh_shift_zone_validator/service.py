"""Service for rh_shift_zone_validator — valida turno, zona y transporte del candidato."""

from __future__ import annotations
import json
import os

_TURNOS_VALIDOS = {"mañana", "tarde", "noche", "rotativo", "partido", "fines_semana"}

_PROMPT = """\
Eres un especialista en selección de personal operativo e industrial en México.

Analiza las respuestas del candidato y valida tres dimensiones contra los requisitos de la vacante.

## Vacante
Turno requerido: {turno_requerido}
Zona/municipio de trabajo: {zona_trabajo}

## Respuestas del candidato
{texto_respuestas}

## Tu tarea

Analiza y devuelve un JSON con esta estructura exacta:

{{
  "turno": {{
    "apto": true/false,
    "turno_candidato": "<turno que puede el candidato, o 'no especificado'>",
    "match": "<exacto|parcial|incompatible>",
    "detalle": "<1 oración>"
  }},
  "zona": {{
    "apto": true/false,
    "zona_candidato": "<zona/municipio donde vive o trabaja actualmente>",
    "distancia_estimada": "<cercano|moderado|lejano|no_determinado>",
    "detalle": "<1 oración>"
  }},
  "transporte": {{
    "riesgo": "<bajo|medio|alto>",
    "medio": "<propio|publico|depende_tercero|no_especificado>",
    "detalle": "<1 oración>"
  }},
  "señales": ["<señal de riesgo 1>", "<señal de riesgo 2>"],
  "recomendacion": "<contratar|revisar|descartar>",
  "resumen": "<2 oraciones con el veredicto global>"
}}

Reglas:
- turno.apto = true si el candidato puede hacer el turno requerido
- zona.apto = true si la distancia estimada es cercano o moderado
- recomendacion = contratar si turno y zona son aptos y riesgo transporte es bajo/medio
- recomendacion = revisar si alguna dimensión es parcial o riesgo transporte es medio
- recomendacion = descartar si turno incompatible O zona lejana Y transporte de alto riesgo
- señales solo las negativas o de alerta; omite si todo es positivo

Devuelve ÚNICAMENTE el JSON, sin texto adicional.
"""


class RhShiftZoneValidatorService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        turno_requerido = context.get("turno_requerido", "no especificado")
        zona_trabajo    = context.get("zona_trabajo", "") or context.get("municipio_trabajo", "") or "no especificada"
        candidato_id    = context.get("candidato_id")
        respuestas      = context.get("respuestas") or self._cargar_respuestas(candidato_id)
        guardar         = context.get("guardar", False)

        if not respuestas:
            return {"ok": False, "error": "respuestas requeridas (directo o via candidato_id)"}

        resultado = self._analizar(turno_requerido, zona_trabajo, respuestas)
        if not resultado["ok"]:
            return resultado

        if candidato_id and guardar:
            self._guardar(candidato_id, resultado["data"])

        return resultado

    def _analizar(self, turno_requerido: str, zona_trabajo: str, respuestas: list | str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

        if isinstance(respuestas, list):
            texto = "\n".join(
                f"- {r.get('pregunta','')}: {r.get('respuesta','')}"
                if isinstance(r, dict) else f"- {r}"
                for r in respuestas
            )
        else:
            texto = str(respuestas)

        prompt = _PROMPT.format(
            turno_requerido=turno_requerido,
            zona_trabajo=zona_trabajo,
            texto_respuestas=texto,
        )

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())

            apto = (
                data.get("turno", {}).get("apto", False)
                and data.get("zona", {}).get("apto", False)
            )

            return {
                "ok": True,
                "data": {
                    "apto":           apto,
                    "turno":          data.get("turno", {}),
                    "zona":           data.get("zona", {}),
                    "transporte":     data.get("transporte", {}),
                    "señales":        data.get("señales", []),
                    "recomendacion":  data.get("recomendacion", "revisar"),
                    "resumen":        data.get("resumen", ""),
                },
            }
        except json.JSONDecodeError:
            return {"ok": False, "error": f"respuesta IA no es JSON válido: {raw[:200]}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _cargar_respuestas(self, candidato_id: str | None) -> list:
        if not candidato_id:
            return []
        try:
            from factory.engine import SupabaseClient
            sb = SupabaseClient({})
            r  = sb.rest_select("respuestas", {"candidato_id": candidato_id}, select="pregunta,respuesta,orden", order="orden")
            return r.get("data") or []
        except Exception:
            return []

    def _guardar(self, candidato_id: str, data: dict) -> None:
        try:
            from factory.engine import SupabaseClient
            sb = SupabaseClient({})
            sb.rest_upsert("scores", {"candidato_id": candidato_id, "detalle": {"shift_zone_validator": data}})
        except Exception:
            pass

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("respuestas") and not context.get("candidato_id"):
            return False, "respuestas o candidato_id requerido"
        if not context.get("turno_requerido") and not context.get("zona_trabajo") and not context.get("municipio_trabajo"):
            return False, "al menos turno_requerido o zona_trabajo es requerido"
        return True, None
