"""Service for rh_retention_predictor — predice riesgo de deserción temprana."""
from __future__ import annotations
import json, os

_PROMPT = """\
Eres especialista en retención de personal operativo e industrial en México.

Puesto: {puesto}

Respuestas del candidato:
{texto_respuestas}

Analiza el riesgo de que este candidato abandone el trabajo en los primeros 3 meses.
Considera: estabilidad laboral previa, razones de salida, distancia al trabajo, transporte,
situación familiar, actitud hacia horarios y condiciones, historial de empleos cortos.

Devuelve ÚNICAMENTE este JSON:
{{
  "score_retencion": <1-10 donde 10 = muy probable que se quede>,
  "riesgo": "<bajo|medio|alto>",
  "meses_estimados": <número estimado de meses que durará, máx 12>,
  "señales": ["<señal de riesgo o estabilidad 1>", "<señal 2>"],
  "recomendacion": "<contratar|revisar|descartar>",
  "resumen": "<2 oraciones con el veredicto>"
}}
"""


class RhRetentionPredictorService:

    def ejecutar(self, context: dict) -> dict:
        candidato_id = context.get("candidato_id")
        respuestas   = context.get("respuestas") or self._cargar_respuestas(candidato_id)
        puesto       = context.get("puesto", "operador")

        if not respuestas:
            return {"ok": False, "error": "respuestas o candidato_id requerido"}

        resultado = self._predecir(puesto, respuestas)
        if not resultado["ok"]:
            return resultado

        if candidato_id and context.get("guardar", False):
            self._guardar(candidato_id, resultado["data"])

        return resultado

    def _predecir(self, puesto: str, respuestas: list | str) -> dict:
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

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                messages=[{"role": "user", "content": _PROMPT.format(puesto=puesto, texto_respuestas=texto)}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return {"ok": True, "data": {"puesto": puesto, **data}}
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
            sb.rest_upsert("scores", {"candidato_id": candidato_id, "detalle": {"retention_predictor": data}})
        except Exception:
            pass
