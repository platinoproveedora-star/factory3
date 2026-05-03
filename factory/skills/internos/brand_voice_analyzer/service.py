"""Service for brand_voice_analyzer - analyzes and defines brand voice."""

from __future__ import annotations

import json
import os
import urllib.request


class BrandVoiceAnalyzerService:

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
        if not context.get("marca"):
            return False, "marca es requerido"
        if not context.get("descripcion"):
            return False, "descripcion es requerido"
        ejemplos = context.get("ejemplos", [])
        if not isinstance(ejemplos, list):
            return False, "ejemplos debe ser una lista de textos"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        marca = context["marca"]
        descripcion = context["descripcion"]
        ejemplos = context.get("ejemplos", [])

        ejemplos_text = ""
        if ejemplos:
            ejemplos_text = "\nEjemplos de contenido existente:\n" + "\n".join(f"- {e}" for e in ejemplos[:5])

        system = (
            "Eres un estratega de marca y experto en brand voice. "
            "Defines la personalidad y voz de marca de forma clara y aplicable. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"Analiza y define la voz de marca para:\n"
            f"Marca: {marca}\n"
            f"Descripcion: {descripcion}"
            f"{ejemplos_text}\n\n"
            "Devuelve JSON:\n"
            '{"tono": [...], "personalidad": [...], "vocabulario_usar": [...], '
            '"vocabulario_evitar": [...], "frases_ejemplo": [...], "resumen": "..."}'
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
