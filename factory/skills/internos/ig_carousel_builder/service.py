"""Service for ig_carousel_builder - generates slide-by-slide copy for Instagram carousels."""
from __future__ import annotations

import json
import os
import urllib.request

_VALID_OBJECTIVES = {"educate", "sell", "entertain", "inspire"}


class IgCarouselBuilderService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("topic") or not isinstance(context["topic"], str):
            return False, "topic es requerido y debe ser texto"
        slide_count = context.get("slide_count")
        if slide_count is not None and (not isinstance(slide_count, int) or slide_count < 3 or slide_count > 10):
            return False, "slide_count debe ser un entero entre 3 y 10"
        objective = context.get("objective")
        if objective is not None and objective not in _VALID_OBJECTIVES:
            return False, f"objective debe ser uno de: {', '.join(sorted(_VALID_OBJECTIVES))}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        topic = context["topic"]
        slide_count = context.get("slide_count", 7)
        objective = context.get("objective", "educate")
        tone = context.get("tone", "profesional y claro")
        brand_voice = context.get("brand_voice", "")

        brand_line = f"Voz de marca: {brand_voice}\n" if brand_voice else ""
        system = (
            "Eres un experto en carruseles de Instagram que generan alto swipe-through rate y engagement. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )
        prompt = (
            f"Genera un carrusel de {slide_count} slides para Instagram sobre:\n"
            f"Tema: {topic}\n"
            f"Objetivo: {objective}\n"
            f"Tono: {tone}\n"
            f"{brand_line}\n"
            "Reglas:\n"
            "- Slide 1 es el hook/portada (determina el swipe-through rate)\n"
            "- Cada slide = UNA idea clara, maximo 2 lineas de body\n"
            "- El ultimo slide siempre tiene CTA fuerte\n"
            "- visual_note es instruccion breve para el disenador\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"cover": {"headline": "...", "subheadline": "..."}, '
            '"slides": [{"number": N, "headline": "...", "body": "...", "visual_note": "..."}], '
            '"last_slide_cta": "...", "caption": "..."}'
        )
        try:
            raw = self._call_anthropic(prompt, system, max_tokens=2000)
            data = json.loads(raw)
            return {"ok": True, "data": data}
        except json.JSONDecodeError:
            return {"ok": True, "data": {"raw": raw}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _call_anthropic(self, prompt: str, system: str, max_tokens: int = 1024) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        parts = [item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"]
        return "\n".join(p for p in parts if p).strip()
