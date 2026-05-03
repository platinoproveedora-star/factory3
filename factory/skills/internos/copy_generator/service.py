"""Service for copy_generator - generates marketing copy variants."""

from __future__ import annotations

import json
import os
import urllib.request

_TIPOS = {"ad", "post", "email", "landing"}
_TONOS = {"urgente", "emocional", "informativo", "humoristico"}


class CopyGeneratorService:

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
        if not context.get("tipo") or context["tipo"] not in _TIPOS:
            return False, f"tipo es requerido y debe ser uno de: {', '.join(sorted(_TIPOS))}"
        if not context.get("producto"):
            return False, "producto es requerido"
        if not context.get("tono") or context["tono"] not in _TONOS:
            return False, f"tono es requerido y debe ser uno de: {', '.join(sorted(_TONOS))}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        tipo = context["tipo"]
        producto = context["producto"]
        tono = context["tono"]
        audiencia = context.get("audiencia", "audiencia general")

        system = (
            "Eres un copywriter experto en marketing digital. "
            "Generas copy persuasivo, claro y orientado a conversiones. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"Genera 3 variantes de copy para:\n"
            f"Tipo: {tipo}\n"
            f"Producto: {producto}\n"
            f"Tono: {tono}\n"
            f"Audiencia: {audiencia}\n\n"
            "Devuelve JSON:\n"
            '{"variantes": [{"id": 1, "titulo": "...", "cuerpo": "...", "cta": "..."}, ...]}'
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
