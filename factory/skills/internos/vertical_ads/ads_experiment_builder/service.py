"""Diseña pruebas A/B de copy, creative, audiencia, placement o presupuesto."""
from __future__ import annotations
import json, os, urllib.request

_ELEMENTOS = {"copy", "creative", "audiencia", "placement", "presupuesto", "oferta", "cta"}


class AdsExperimentBuilderService:

    def ejecutar(self, context: dict) -> dict:
        elemento  = context.get("elemento", "").strip()
        campana   = context.get("campana", "").strip()
        hipotesis = context.get("hipotesis", "").strip()

        if not elemento or elemento not in _ELEMENTOS:
            return {"ok": False, "error": f"elemento requerido — válidos: {', '.join(_ELEMENTOS)}"}
        if not campana:
            return {"ok": False, "error": "campana requerido"}
        if not hipotesis:
            return {"ok": False, "error": "hipotesis requerido"}

        presupuesto  = context.get("presupuesto_prueba", "")
        duracion     = int(context.get("duracion_dias", 7))
        metrica_exito = context.get("metrica_exito", "CPL")
        variantes    = int(context.get("num_variantes", 2))

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "elemento": elemento}}

        prompt = (
            f"Diseña un experimento A/B publicitario riguroso.\n"
            f"Elemento a probar: {elemento}\n"
            f"Campaña/contexto: {campana}\n"
            f"Hipótesis: {hipotesis}\n"
            f"Número de variantes: {variantes}\n"
            f"Duración: {duracion} días\n"
            f"Presupuesto para prueba: {presupuesto or 'no especificado'}\n"
            f"Métrica de éxito: {metrica_exito}\n\n"
            "Devuelve JSON con:\n"
            '{"nombre_experimento":"...","hipotesis":"...","elemento_probado":"...",'
            '"variantes":[{"id":"A|B|C","nombre":"...","descripcion":"...","cambio_especifico":"..."}],'
            '"control":"A","metricas":{"primaria":"...","secundarias":[]},'
            '"duracion_dias":0,"tamano_muestra_minimo":"...",'
            '"criterio_ganador":"...","cuando_detener":"...","sesgos_a_evitar":[],'
            '"calendario":[{"dia":0,"accion":"..."}]}'
        )
        return self._haiku(prompt, "Eres un experto en experimentación y CRO en publicidad digital. Responde SIEMPRE en JSON válido.")

    def _haiku(self, prompt: str, system: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({"model": "claude-haiku-4-5-20251001", "max_tokens": 2048,
                    "system": system, "messages": [{"role": "user", "content": prompt}]}).encode(),
                headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = json.loads(r.read().decode())["content"][0]["text"].strip()
            try:
                return {"ok": True, "data": json.loads(raw)}
            except Exception:
                return {"ok": True, "data": {"raw": raw}}
        except Exception as e:
            return {"ok": False, "error": str(e)}
