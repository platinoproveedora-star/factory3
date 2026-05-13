"""Service for ig_alt_text_generator - generates descriptive alt text for Instagram images."""
from __future__ import annotations

import json
import os
import urllib.request

_VALID_LANGUAGES = {"es", "en"}


class IgAltTextGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("image_description") or not isinstance(context["image_description"], str):
            return False, "image_description es requerido y debe ser texto"
        language = context.get("language")
        if language is not None and language not in _VALID_LANGUAGES:
            return False, f"language debe ser uno de: {', '.join(sorted(_VALID_LANGUAGES))}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        image_description = context["image_description"]
        ctx = context.get("context", "")
        language = context.get("language", "es")

        ctx_line = f"Contexto de la publicacion: {ctx}\n" if ctx else ""
        lang_instruction = "en español" if language == "es" else "in English"

        system = (
            "Eres un experto en accesibilidad web y SEO para Instagram. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )
        prompt = (
            f"Genera alt text para esta imagen de Instagram ({lang_instruction}):\n"
            f"Descripcion de la imagen: {image_description}\n"
            f"{ctx_line}\n"
            "Reglas del alt text:\n"
            "- Maximo 125 caracteres\n"
            "- No empieces con 'imagen de' ni 'foto de'\n"
            "- Describe lo mas importante primero\n"
            "- Incluye keywords relevantes de forma natural\n"
            "- Debe ser util para lectores de pantalla\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"alt_text": "...", "character_count": N, "seo_keywords": [...]}'
        )
        try:
            raw = self._call_anthropic(prompt, system, max_tokens=512)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
                raw = raw.strip()
            data = json.loads(raw)
            if "alt_text" in data:
                data["character_count"] = len(data["alt_text"])
            return {"ok": True, "data": data}
        except json.JSONDecodeError:
            return {"ok": True, "data": {"alt_text": raw, "character_count": len(raw)}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _call_anthropic(self, prompt: str, system: str, max_tokens: int = 512) -> str:
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
