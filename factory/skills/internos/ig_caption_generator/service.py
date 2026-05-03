"""Service for ig_caption_generator - generates Instagram captions with CTA."""

from __future__ import annotations

import json
import os
import urllib.request


class IgCaptionGeneratorService:

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
        if not isinstance(context["topic"], str):
            return False, "topic debe ser texto"
        for field in ("tone", "brand_voice", "cta"):
            val = context.get(field)
            if val is not None and not isinstance(val, str):
                return False, f"{field} debe ser texto"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        topic = context["topic"]
        tone = context.get("tone", "profesional y cercano")
        brand_voice = context.get("brand_voice", "")
        cta = context.get("cta", "")

        system = (
            "Eres un experto en marketing de contenidos para Instagram. "
            "Escribes captions que generan engagement, usan emojis con criterio "
            "y tienen una estructura clara: hook en la primera linea, desarrollo y CTA. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )

        brand_line = f"Voz de marca: {brand_voice}\n" if brand_voice else ""
        cta_line = f"CTA: {cta}\n" if cta else ""

        prompt = (
            f"Genera un caption completo para Instagram sobre:\n"
            f"Tema: {topic}\n"
            f"Tono: {tone}\n"
            f"{brand_line}"
            f"{cta_line}"
            "\nRequisitos:\n"
            "- Primera linea es el hook (lo que se ve antes del 'ver mas')\n"
            "- Cuerpo con saltos de linea para que el texto respire\n"
            "- Emojis integrados de forma natural, no al final en bloque\n"
            "- CTA claro al final\n"
            "- Listo para copiar y pegar en Instagram\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"caption": "...", "character_count": N}'
        )

        try:
            raw = self._call_anthropic(prompt, system)
            data = json.loads(raw)
            if "caption" in data and "character_count" not in data:
                data["character_count"] = len(data["caption"])
            return {"ok": True, "data": data}
        except json.JSONDecodeError:
            return {"ok": True, "data": {"caption": raw, "character_count": len(raw)}}
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
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        parts = [item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"]
        return "\n".join(p for p in parts if p).strip()
