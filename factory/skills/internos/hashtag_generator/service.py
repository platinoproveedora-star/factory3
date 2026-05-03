"""Service for hashtag_generator - generates strategic hashtags."""

from __future__ import annotations

import json
import os
import urllib.request

_REDES = {"instagram", "linkedin", "twitter", "tiktok"}


class HashtagGeneratorService:

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
        if not context.get("tema"):
            return False, "tema es requerido"
        if not context.get("industria"):
            return False, "industria es requerido"
        if not context.get("red_social") or context["red_social"] not in _REDES:
            return False, f"red_social es requerido: {', '.join(sorted(_REDES))}"
        cantidad = context.get("cantidad", 20)
        if not isinstance(cantidad, int) or cantidad < 5 or cantidad > 50:
            return False, "cantidad debe ser entre 5 y 50"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        tema = context["tema"]
        industria = context["industria"]
        red = context["red_social"]
        cantidad = context.get("cantidad", 20)

        system = (
            "Eres un experto en estrategia de hashtags para redes sociales. "
            "Conoces las tendencias y el alcance de cada hashtag por plataforma. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"Genera {cantidad} hashtags estratégicos para {red}:\n"
            f"Tema: {tema}\n"
            f"Industria: {industria}\n\n"
            "Agrúpalos por alcance. Devuelve JSON:\n"
            '{"red_social": "...", "hashtags": {"viral": [...], "medio": [...], "nicho": [...]}}'
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
            "max_tokens": 1024,
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
