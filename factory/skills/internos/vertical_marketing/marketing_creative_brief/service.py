"""Crea brief creativo para imagen, video, carrusel o anuncio."""
from __future__ import annotations
import json, os, urllib.request

_FORMATOS = {"imagen", "video", "carrusel", "anuncio", "story", "reel"}


class MarketingCreativeBriefService:

    def ejecutar(self, context: dict) -> dict:
        formato   = context.get("formato", "").strip()
        producto  = context.get("producto", "").strip()
        audiencia = context.get("audiencia", "").strip()
        objetivo  = context.get("objetivo", "").strip()

        if not formato or formato not in _FORMATOS:
            return {"ok": False, "error": f"formato requerido — válidos: {', '.join(_FORMATOS)}"}
        if not producto:
            return {"ok": False, "error": "producto requerido"}
        if not audiencia:
            return {"ok": False, "error": "audiencia requerido"}
        if not objetivo:
            return {"ok": False, "error": "objetivo requerido"}

        tono      = context.get("tono", "profesional")
        plataforma = context.get("plataforma", "meta")

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "formato": formato, "producto": producto}}

        specs_formato = {
            "imagen":   "1080x1080px o 1200x628px, JPG/PNG, máx 20% texto",
            "video":    "9:16 o 1:1, MP4, 15-30 segs para ads, 60 segs para feed",
            "carrusel": "hasta 10 tarjetas, 1080x1080px por tarjeta",
            "anuncio":  "según plataforma — Meta: 1200x628 o 1080x1080",
            "story":    "1080x1920px, 9:16, máx 15 segs video",
            "reel":     "1080x1920px, 9:16, 15-90 segs",
        }
        prompt = (
            f"Crea un brief creativo completo.\n"
            f"Formato: {formato}\n"
            f"Producto/Servicio: {producto}\n"
            f"Audiencia: {audiencia}\n"
            f"Objetivo: {objetivo}\n"
            f"Tono: {tono}\n"
            f"Plataforma: {plataforma}\n"
            f"Specs técnicas: {specs_formato.get(formato, '')}\n\n"
            "Devuelve JSON con:\n"
            '{"concepto_creativo":"...","mensaje_central":"...","tono_visual":"...","tono_verbal":"...",'
            '"elementos_visuales":["..."],"copy_guia":{"headline":"...","cuerpo":"...","cta":"..."},'
            '"referencias_estilo":["..."],"specs_tecnicos":{"dimension":"...","duracion":"...","formato_archivo":"..."},'
            '"do":["..."],"dont":["..."],"kpi_creativo":"..."}'
        )
        return self._haiku(prompt, "Eres un director creativo senior en marketing digital. Responde SIEMPRE en JSON válido.")

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
