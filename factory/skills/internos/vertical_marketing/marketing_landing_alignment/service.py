"""Revisa coherencia entre anuncio, oferta, landing y conversión. Devuelve score y gaps."""
from __future__ import annotations
import json, os, urllib.request


class MarketingLandingAlignmentService:

    def ejecutar(self, context: dict) -> dict:
        anuncio_copy  = context.get("anuncio_copy", "").strip()
        oferta        = context.get("oferta", "").strip()
        landing_copy  = context.get("landing_copy", "").strip()
        cta           = context.get("cta", "").strip()

        if not anuncio_copy:
            return {"ok": False, "error": "anuncio_copy requerido"}
        if not oferta:
            return {"ok": False, "error": "oferta requerido"}
        if not landing_copy:
            return {"ok": False, "error": "landing_copy requerido"}

        objetivo      = context.get("objetivo", "conversión")
        audiencia     = context.get("audiencia", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True}}

        prompt = (
            f"Analiza la coherencia del funnel de conversión.\n\n"
            f"ANUNCIO (copy):\n{anuncio_copy}\n\n"
            f"OFERTA:\n{oferta}\n\n"
            f"LANDING PAGE (copy principal):\n{landing_copy}\n\n"
            f"CTA: {cta or 'no especificado'}\n"
            f"Objetivo: {objetivo}\n"
            f"Audiencia: {audiencia or 'no especificada'}\n\n"
            "Evalúa: consistencia de mensaje, promesa vs entrega, fricción, claridad del CTA y match de audiencia.\n"
            "Devuelve JSON con:\n"
            '{"score_coherencia":0-100,"nivel":"alto|medio|bajo","gaps":[],'
            '"puntos_fuertes":[],"recomendaciones":[],'
            '"mensaje_anuncio_vs_landing":"alineado|parcial|desalineado",'
            '"riesgo_abandono":"alto|medio|bajo","accion_prioritaria":"..."}'
        )
        return self._haiku(prompt, "Eres un experto en CRO y optimización de funnels de conversión. Responde SIEMPRE en JSON válido.")

    def _haiku(self, prompt: str, system: str) -> dict:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY no configurada"}
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-haiku-4-5-20251001", "max_tokens": 1024,
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
