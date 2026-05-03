"""Service for ig_story_script - generates Instagram Story script with interactive stickers."""
from __future__ import annotations

import json
import os
import urllib.request


class IgStoryScriptService:

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
        frame_count = context.get("frame_count")
        if frame_count is not None and (not isinstance(frame_count, int) or frame_count < 3 or frame_count > 10):
            return False, "frame_count debe ser un entero entre 3 y 10"
        for field in ("include_poll", "include_question"):
            val = context.get(field)
            if val is not None and not isinstance(val, bool):
                return False, f"{field} debe ser booleano"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        topic = context["topic"]
        frame_count = context.get("frame_count", 5)
        include_poll = context.get("include_poll", True)
        include_question = context.get("include_question", False)
        cta = context.get("cta", "")
        tone = context.get("tone", "cercano y dinamico")

        stickers_note = ""
        if include_poll:
            stickers_note += "- Incluir al menos un sticker de encuesta (poll)\n"
        if include_question:
            stickers_note += "- Incluir al menos un sticker de pregunta (question)\n"
        cta_line = f"CTA deseado: {cta}\n" if cta else ""

        system = (
            "Eres un experto en Instagram Stories que maximizan engagement. "
            "Los stickers interactivos (polls, preguntas) aumentan el engagement ratio drasticamente. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )
        prompt = (
            f"Genera un guion de {frame_count} frames para Instagram Stories sobre:\n"
            f"Tema: {topic}\n"
            f"Tono: {tone}\n"
            f"{cta_line}"
            f"{stickers_note}\n"
            "Reglas:\n"
            "- Cada frame dura ~5 segundos\n"
            "- Texto corto por frame (max 10 palabras visibles)\n"
            "- Stickers solo en frames donde tenga sentido\n"
            "- Ultimo frame tiene el CTA con swipe up o link\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"frames": [{"number": N, "text": "...", '
            '"sticker": null, "sticker_config": "...", "bg_color_suggestion": "...", '
            '"duration_seconds": 5}], "swipe_up_cta": "..."}'
            "\n\nsticker puede ser null, \"poll\", \"question\", \"slider\" o \"countdown\"."
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
