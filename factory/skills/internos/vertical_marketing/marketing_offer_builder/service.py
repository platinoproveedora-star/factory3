"""Estructura oferta completa: promesa, beneficios, objeciones y CTA con IA."""
from __future__ import annotations
import json, os, urllib.request


class MarketingOfferBuilderService:

    def ejecutar(self, context: dict) -> dict:
        producto  = context.get("producto", "").strip()
        audiencia = context.get("audiencia", "").strip()
        if not producto:
            return {"ok": False, "error": "producto requerido"}
        if not audiencia:
            return {"ok": False, "error": "audiencia requerido"}

        precio         = context.get("precio", "")
        diferenciador  = context.get("diferenciador", "")
        competidores   = context.get("competidores", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "producto": producto}}

        prompt = (
            f"Estructura una oferta de marketing irresistible.\n"
            f"Producto/Servicio: {producto}\n"
            f"Audiencia objetivo: {audiencia}\n"
            f"Precio/rango: {precio or 'no definido'}\n"
            f"Diferenciador clave: {diferenciador or 'identificar'}\n"
            f"Competidores: {competidores or 'no especificado'}\n\n"
            "Devuelve JSON con:\n"
            '{"promesa_principal":"...","subtitulo":"...","beneficios":[{"titulo":"...","descripcion":"..."}],'
            '"para_quien":"...","no_para_quien":"...","objeciones":[{"objecion":"...","respuesta":"..."}],'
            '"diferenciadores":[],"garantia":"...","urgencia":"...","cta_principal":"...","cta_secundario":"..."}'
        )
        return self._haiku(prompt, "Eres un experto en marketing de respuesta directa y copywriting persuasivo. Responde SIEMPRE en JSON válido.")

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
