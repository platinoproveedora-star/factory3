"""Service for rh_dimension_analyzer — analiza una dimensión específica sobre respuestas del candidato."""

from __future__ import annotations
import json
import os

_DIMENSIONES = {
    "conducta": (
        "Analiza el perfil conductual del candidato: confiabilidad, actitud hacia el trabajo, "
        "historial de conflictos, manejo de autoridad y riesgo de comportamiento agresivo."
    ),
    "fisico": (
        "Evalúa indicadores de resistencia física para trabajo operativo pesado: "
        "historial de trabajo de campo, horarios extendidos, condiciones difíciles y salud declarada."
    ),
    "compromiso": (
        "Predice el nivel de compromiso y ausentismo: historial laboral, razones de salida, "
        "estabilidad familiar, distancia al trabajo y disponibilidad de horario."
    ),
    "maquinaria": (
        "Valida el conocimiento técnico de maquinaria o vehículos: marcas, modelos, "
        "tipos de licencia, mantenimiento básico y años de experiencia específica."
    ),
    "rutas": (
        "Clasifica la experiencia por tipo de ruta: urbana, carretera federal, "
        "foránea larga distancia, zonas específicas y conocimiento del territorio."
    ),
    "tecnico": (
        "Analiza profundidad técnica general: herramientas usadas, certificaciones, "
        "capacitaciones, resolución de problemas en campo y autonomía operativa."
    ),
}

_ESCALA = "Califica del 1 al 10 donde 10 es excelente para el puesto operativo."


class RhDimensionAnalyzerService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        dimension  = context["dimension"]
        candidato_id = context.get("candidato_id")
        respuestas = context.get("respuestas") or self._cargar_respuestas(candidato_id)
        puesto     = context.get("puesto", "operador")
        extra      = context.get("contexto_extra", "")

        if not respuestas:
            return {"ok": False, "error": "respuestas requeridas (directo o via candidato_id)"}

        resultado = self._analizar(dimension, respuestas, puesto, extra)
        if not resultado["ok"]:
            return resultado

        if candidato_id and context.get("guardar", False):
            self._guardar(candidato_id, dimension, resultado["data"])

        return resultado

    def _analizar(self, dimension: str, respuestas: list | str, puesto: str, extra: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}

        if isinstance(respuestas, list):
            texto_respuestas = "\n".join(
                f"- {r.get('pregunta','')}: {r.get('respuesta','')}"
                if isinstance(r, dict) else f"- {r}"
                for r in respuestas
            )
        else:
            texto_respuestas = str(respuestas)

        instruccion = _DIMENSIONES[dimension]

        prompt = (
            f"Eres un especialista en evaluación de candidatos para puestos operativos e industriales en México.\n\n"
            f"Puesto evaluado: {puesto}\n"
            f"Dimensión a analizar: {dimension.upper()}\n"
            f"Instrucción: {instruccion}\n"
            f"{_ESCALA}\n"
            f"{f'Contexto adicional: {extra}' if extra else ''}\n\n"
            f"Respuestas del candidato:\n{texto_respuestas}\n\n"
            f"Devuelve ÚNICAMENTE un JSON con esta estructura:\n"
            f'{{"score": <1-10>, "nivel": "<bajo|medio|alto>", '
            f'"resumen": "<2 oraciones>", "señales": ["<señal1>","<señal2>"], '
            f'"recomendacion": "<contratar|revisar|descartar>"}}'
        )

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return {"ok": True, "data": {"dimension": dimension, "puesto": puesto, **data}}
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

    def _guardar(self, candidato_id: str, dimension: str, data: dict) -> None:
        try:
            from factory.engine import SupabaseClient
            sb = SupabaseClient({})
            sb.rest_upsert("scores", {
                "candidato_id": candidato_id,
                "score_total":  data.get("score", 0) * 10,
                "detalle":      {f"dimension_{dimension}": data},
            })
        except Exception:
            pass

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        dimension = context.get("dimension")
        if not dimension:
            return False, f"dimension requerida. Disponibles: {list(_DIMENSIONES.keys())}"
        if dimension not in _DIMENSIONES:
            return False, f"dimension '{dimension}' inválida. Disponibles: {list(_DIMENSIONES.keys())}"
        if not context.get("respuestas") and not context.get("candidato_id"):
            return False, "respuestas o candidato_id requerido"
        return True, None
