"""Planea campaña por objetivo, oferta, audiencia, canales, funnel y KPIs con IA."""
from __future__ import annotations
import json, os, urllib.request


class MarketingCampaignPlannerService:

    def ejecutar(self, context: dict) -> dict:
        objetivo   = context.get("objetivo", "").strip()
        producto   = context.get("producto", "").strip()
        audiencia  = context.get("audiencia", "").strip()
        if not objetivo:
            return {"ok": False, "error": "objetivo requerido"}
        if not producto:
            return {"ok": False, "error": "producto requerido"}
        if not audiencia:
            return {"ok": False, "error": "audiencia requerido"}

        duracion    = int(context.get("duracion_dias", 30))
        presupuesto = context.get("presupuesto", "no definido")
        canales     = context.get("canales", "")
        funnel      = context.get("funnel", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "objetivo": objetivo, "producto": producto}}

        prompt = (
            f"Crea un plan de campaña de marketing completo.\n"
            f"Objetivo: {objetivo}\n"
            f"Producto/Servicio: {producto}\n"
            f"Audiencia: {audiencia}\n"
            f"Duración: {duracion} días\n"
            f"Presupuesto: {presupuesto}\n"
            f"Canales preferidos: {canales or 'definir según objetivo'}\n"
            f"Etapa del funnel: {funnel or 'full funnel'}\n\n"
            "Devuelve JSON con:\n"
            '{"nombre_campana":"...","objetivo_smart":"...","propuesta_valor":"...",'
            '"fases":[{"nombre":"...","dias":"...","objetivo":"...","acciones":[]}],'
            '"canales":[{"canal":"...","rol":"...","budget_pct":0}],'
            '"mensajes_clave":[],"kpis":[{"metrica":"...","meta":"..."}],'
            '"calendario_resumen":"...","riesgos":[]}'
        )
        return self._haiku(prompt, "Eres un estratega de marketing digital senior. Responde SIEMPRE en JSON válido.")

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
