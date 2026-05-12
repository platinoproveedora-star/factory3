"""Analiza CTR, CPC, CPL, CPA, ROAS, frecuencia y fatiga. Diagnostica y recomienda."""
from __future__ import annotations
import json, os, urllib.request


class AdsPerformanceAnalyzerService:

    def ejecutar(self, context: dict) -> dict:
        metricas  = context.get("metricas") or {}
        objetivo  = context.get("objetivo", "").strip()

        if not metricas:
            return {"ok": False, "error": "metricas requerido (dict con CTR, CPC, CPL, CPA, ROAS, etc.)"}
        if not objetivo:
            return {"ok": False, "error": "objetivo requerido"}

        industria  = context.get("industria", "general")
        plataforma = context.get("plataforma", "meta")
        periodo    = context.get("periodo", "últimos 7 días")
        presupuesto_gastado = context.get("presupuesto_gastado", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "metricas_recibidas": list(metricas.keys())}}

        metricas_txt = "\n".join(f"- {k}: {v}" for k, v in metricas.items())
        prompt = (
            f"Analiza el performance de campañas publicitarias.\n"
            f"Plataforma: {plataforma}\n"
            f"Objetivo: {objetivo}\n"
            f"Industria: {industria}\n"
            f"Período: {periodo}\n"
            f"Presupuesto gastado: {presupuesto_gastado or 'no especificado'}\n\n"
            f"MÉTRICAS:\n{metricas_txt}\n\n"
            "Diagnostica: ¿qué está bien, qué está mal, hay fatiga, hay problemas de calidad?\n"
            "Devuelve JSON con:\n"
            '{"score_general":0-100,"diagnostico":"...","estado":"saludable|atención|critico",'
            '"metricas_analizadas":[{"metrica":"...","valor":"...","benchmark":"...","evaluacion":"bueno|regular|malo","razon":"..."}],'
            '"fatiga_detectada":false,"problemas":[],"fortalezas":[],'
            '"recomendaciones_inmediatas":[],"recomendaciones_estrategicas":[]}'
        )
        return self._haiku(prompt, "Eres un analista senior de performance publicitario. Responde SIEMPRE en JSON válido.")

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
