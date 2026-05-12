"""Genera 3 variantes de copy para meta, google, linkedin, email o landing."""
from __future__ import annotations
import json, os, urllib.request

_PLATAFORMAS = {"meta", "google", "linkedin", "email", "landing", "tiktok"}
_TONOS       = {"urgente", "emocional", "informativo", "humoristico", "autoritativo"}


class MarketingCopyGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        producto   = context.get("producto", "").strip()
        plataforma = context.get("plataforma", "meta").strip()
        tono       = context.get("tono", "emocional").strip()
        audiencia  = context.get("audiencia", "").strip()

        if not producto:
            return {"ok": False, "error": "producto requerido"}
        if plataforma not in _PLATAFORMAS:
            return {"ok": False, "error": f"plataforma inválida — válidas: {', '.join(_PLATAFORMAS)}"}
        if tono not in _TONOS:
            return {"ok": False, "error": f"tono inválido — válidos: {', '.join(_TONOS)}"}

        objetivo = context.get("objetivo", "")
        oferta   = context.get("oferta", "")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "producto": producto, "plataforma": plataforma}}

        specs = {
            "meta":    "headline ≤40 chars, texto principal ≤125 chars, descripción ≤30 chars",
            "google":  "headline ≤30 chars, descripción ≤90 chars",
            "linkedin": "headline ≤200 chars, texto ≤600 chars",
            "email":   "asunto ≤50 chars, preview ≤90 chars, cuerpo 3-5 párrafos",
            "landing": "headline ≤10 palabras, subheadline 1 línea, bullets beneficios, CTA",
            "tiktok":  "hook ≤3 segs, texto ≤150 chars, hashtags",
        }
        prompt = (
            f"Genera 3 variantes de copy para {plataforma}.\n"
            f"Producto/Servicio: {producto}\n"
            f"Audiencia: {audiencia or 'general'}\n"
            f"Tono: {tono}\n"
            f"Objetivo: {objetivo or 'conversión'}\n"
            f"Oferta especial: {oferta or 'ninguna'}\n"
            f"Specs de plataforma: {specs.get(plataforma, '')}\n\n"
            "Devuelve JSON con:\n"
            '{"plataforma":"...","variantes":[{"id":1,"headline":"...","cuerpo":"...","cta":"...","notas":"..."}]}'
        )
        return self._haiku(prompt, "Eres un copywriter experto en publicidad digital. Responde SIEMPRE en JSON válido.")

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
