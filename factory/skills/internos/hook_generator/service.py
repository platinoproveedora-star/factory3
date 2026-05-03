"""Service for hook_generator - generates viral hooks for content."""

from __future__ import annotations

import json
import os
import urllib.request

_FORMATOS = {"video", "post", "reel", "email"}


class HookGeneratorService:

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
        if not context.get("formato") or context["formato"] not in _FORMATOS:
            return False, f"formato es requerido: {', '.join(sorted(_FORMATOS))}"
        if not context.get("audiencia"):
            return False, "audiencia es requerido"
        cantidad = context.get("cantidad", 10)
        if not isinstance(cantidad, int) or cantidad < 3 or cantidad > 20:
            return False, "cantidad debe ser entre 3 y 20"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        tema = context["tema"]
        formato = context["formato"]
        audiencia = context["audiencia"]
        cantidad = context.get("cantidad", 10)

        system = (
            "Eres un experto en contenido viral y copywriting de hooks. "
            "Creas primeras líneas irresistibles que detienen el scroll. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"Genera {cantidad} hooks virales para:\n"
            f"Tema: {tema}\n"
            f"Formato: {formato}\n"
            f"Audiencia: {audiencia}\n\n"
            "Devuelve JSON:\n"
            '{"hooks": [{"tipo": "pregunta|dato|historia|controversia|beneficio", "texto": "..."}]}'
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
