"""Service for ig_reel_script - generates complete Reel script optimized for watch time."""
from __future__ import annotations

import json
import os
import urllib.request

_VALID_HOOK_TYPES = {"question", "statement", "statistic", "story"}


class IgReelScriptService:

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
        duration = context.get("duration_seconds")
        if duration is not None and (not isinstance(duration, int) or duration < 15 or duration > 90):
            return False, "duration_seconds debe ser un entero entre 15 y 90"
        hook_type = context.get("hook_type")
        if hook_type is not None and hook_type not in _VALID_HOOK_TYPES:
            return False, f"hook_type debe ser uno de: {', '.join(sorted(_VALID_HOOK_TYPES))}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        topic = context["topic"]
        duration = context.get("duration_seconds", 30)
        tone = context.get("tone", "dinamico y directo")
        hook_type = context.get("hook_type", "statement")

        system = (
            "Eres un experto en guiones para Instagram Reels. "
            "Escribes guiones que maximizan el watch time, la senal mas importante del algoritmo 2025. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )
        prompt = (
            f"Genera un guion completo para un Reel de {duration} segundos sobre:\n"
            f"Tema: {topic}\n"
            f"Tono: {tone}\n"
            f"Tipo de hook: {hook_type}\n\n"
            "Reglas criticas:\n"
            "- El hook debe capturar atencion en los primeros 1-3 segundos\n"
            "- Los segmentos deben sumar exactamente los segundos indicados\n"
            "- Cada segmento tiene accion visual + texto hablado\n"
            "- CTA fuerte en los ultimos 3 segundos\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"hook": "...", "segments": [{"second_start": N, "action": "...", "spoken_text": "..."}], '
            '"cta": "...", "caption_suggestion": "...", "total_seconds": N}'
        )
        try:
            raw = self._call_anthropic(prompt, system, max_tokens=1500)
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
