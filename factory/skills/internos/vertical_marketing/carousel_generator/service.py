"""Service for carousel_generator - generates carousel content for Instagram/LinkedIn."""

from __future__ import annotations

import json
import os
import urllib.request


class CarouselGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        if not context.get("topic"):
            return False, "topic es requerido"
        slides = context.get("slides", 5)
        if not isinstance(slides, int) or slides < 2 or slides > 15:
            return False, "slides debe ser un entero entre 2 y 15"
        tone = context.get("tone", "casual")
        if tone not in ("casual", "professional"):
            return False, "tone debe ser casual o professional"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        topic = context["topic"]
        slides = context.get("slides", 5)
        tone = context.get("tone", "casual")
        brand = context.get("brand", "")
        brand_line = f"Marca: {brand}\n" if brand else ""

        system = (
            "Eres un experto en marketing de contenidos para redes sociales. "
            "Generas carruseles virales y de alto engagement. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"{brand_line}"
            f"Genera un carrusel de {slides} slides sobre: {topic}\n"
            f"Tono: {tone}\n\n"
            "Devuelve JSON con esta estructura exacta:\n"
            '{"titulo_carrusel": "...", "slides": [{"numero": 1, "titulo": "...", "cuerpo": "...", "cta": "..."}, ...]}'
        )

        try:
            raw = self._call_anthropic(prompt, system)
            data = json.loads(raw)
            return {"ok": True, "data": data}
        except json.JSONDecodeError:
            return {"ok": True, "data": {"raw": raw}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _call_anthropic(self, prompt: str, system: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 2048,
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
