"""Service for ig_hashtag_generator - generates strategic Instagram hashtags grouped by reach."""
from __future__ import annotations

import json
import os
import urllib.request

_VALID_AUDIENCE_SIZES = {"mass", "mid", "niche"}


class IgHashtagGeneratorService:

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
        audience_size = context.get("audience_size")
        if audience_size is not None and audience_size not in _VALID_AUDIENCE_SIZES:
            return False, f"audience_size debe ser uno de: {', '.join(sorted(_VALID_AUDIENCE_SIZES))}"
        count = context.get("count")
        if count is not None and (not isinstance(count, int) or count < 1 or count > 50):
            return False, "count debe ser un entero entre 1 y 50"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        topic = context["topic"]
        niche = context.get("niche", "")
        audience_size = context.get("audience_size", "mid")
        count = context.get("count", 30)

        niche_line = f"Nicho: {niche}\n" if niche else ""
        system = (
            "Eres un experto en estrategia de hashtags para Instagram. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )
        prompt = (
            f"Genera {count} hashtags para Instagram sobre:\n"
            f"Tema: {topic}\n"
            f"{niche_line}"
            f"Preferencia de alcance: {audience_size}\n\n"
            "Grupos de alcance:\n"
            "- mass: mas de 1 millon de posts (alta competencia)\n"
            "- mid: entre 100K y 1 millon de posts\n"
            "- niche: menos de 100K posts (alta especificidad)\n\n"
            f"Distribuye {count} hashtags estrategicamente priorizando el grupo '{audience_size}'.\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"hashtags": {"mass": [...], "mid": [...], "niche": [...]}, "total": N, "strategy_note": "..."}'
        )
        try:
            raw = self._call_anthropic(prompt, system)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
                raw = raw.strip()
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
