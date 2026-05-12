"""Genera reporte ejecutivo de campaña con resultados, aprendizajes y próximos pasos."""
from __future__ import annotations
import json, os, urllib.request


class MarketingReportGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        campana           = context.get("campana", "").strip()
        metricas          = context.get("metricas") or {}
        periodo           = context.get("periodo", "").strip()
        objetivo_original = context.get("objetivo_original", "").strip()

        if not campana:
            return {"ok": False, "error": "campana requerido"}
        if not metricas:
            return {"ok": False, "error": "metricas requerido (dict con resultados)"}
        if not objetivo_original:
            return {"ok": False, "error": "objetivo_original requerido"}

        presupuesto = context.get("presupuesto_invertido", "")
        canales     = context.get("canales", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "campana": campana}}

        metricas_txt = "\n".join(f"- {k}: {v}" for k, v in metricas.items())
        prompt = (
            f"Genera un reporte ejecutivo de campaña de marketing.\n\n"
            f"Campaña: {campana}\n"
            f"Período: {periodo or 'no especificado'}\n"
            f"Objetivo original: {objetivo_original}\n"
            f"Presupuesto invertido: {presupuesto or 'no especificado'}\n"
            f"Canales: {canales or 'no especificado'}\n\n"
            f"MÉTRICAS OBTENIDAS:\n{metricas_txt}\n\n"
            "Devuelve JSON con:\n"
            '{"resumen_ejecutivo":"...","objetivo_alcanzado":true|false,"cumplimiento_pct":0-100,'
            '"resultados_clave":[{"metrica":"...","resultado":"...","vs_objetivo":"...","evaluacion":"bueno|regular|malo"}],'
            '"aprendizajes":[],"que_funciono":[],"que_no_funciono":[],'
            '"recomendaciones_proxima":[],"acciones_inmediatas":[],'
            '"score_campana":0-100,"conclusion":"..."}'
        )
        return self._haiku(prompt, "Eres un analista senior de marketing digital con experiencia en reportes ejecutivos. Responde SIEMPRE en JSON válido.")

    def _haiku(self, prompt: str, system: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-haiku-4-5-20251001", "max_tokens": 2048,
                    "system": system, "messages": [{"role": "user", "content": prompt}],
                }).encode(),
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
