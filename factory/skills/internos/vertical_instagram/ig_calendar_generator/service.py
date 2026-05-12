"""Service for ig_calendar_generator - generates monthly Instagram editorial calendar."""
from __future__ import annotations

import json
import os
import urllib.request

_VALID_FORMATS = {"reel", "carousel", "post", "story"}


class IgCalendarGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        month = context.get("month")
        if month is None or not isinstance(month, int) or month < 1 or month > 12:
            return False, "month es requerido y debe ser un entero entre 1 y 12"
        year = context.get("year")
        if year is None or not isinstance(year, int) or year < 2024:
            return False, "year es requerido y debe ser un entero >= 2024"
        if not context.get("niche") or not isinstance(context["niche"], str):
            return False, "niche es requerido y debe ser texto"
        posts_per_week = context.get("posts_per_week")
        if posts_per_week is not None and (not isinstance(posts_per_week, int) or posts_per_week < 1 or posts_per_week > 7):
            return False, "posts_per_week debe ser un entero entre 1 y 7"
        formats = context.get("formats")
        if formats is not None:
            if not isinstance(formats, list) or not formats:
                return False, "formats debe ser una lista no vacia"
            invalid = [f for f in formats if f not in _VALID_FORMATS]
            if invalid:
                return False, f"formatos invalidos: {invalid}. Validos: {sorted(_VALID_FORMATS)}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        month = context["month"]
        year = context["year"]
        niche = context["niche"]
        brand_name = context.get("brand_name", "")
        posts_per_week = context.get("posts_per_week", 5)
        formats = context.get("formats", ["reel", "carousel", "post"])

        brand_line = f"Marca: {brand_name}\n" if brand_name else ""
        system = (
            "Eres un estratega de contenido para Instagram. Creas calendarios editoriales que equilibran "
            "formatos, objetivos y frecuencia de publicacion. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )
        month_names = {1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
                       7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}
        prompt = (
            f"Genera un calendario editorial de Instagram para {month_names[month]} {year}:\n"
            f"Nicho: {niche}\n"
            f"{brand_line}"
            f"Posts por semana: {posts_per_week}\n"
            f"Formatos disponibles: {', '.join(formats)}\n\n"
            "Genera 4 semanas. Alterna formatos y objetivos (reach, engagement, sales, dms). "
            "Los temas deben ser relevantes al nicho.\n\n"
            "Devuelve unicamente este JSON:\n"
            '{"month": N, "year": N, "total_posts": N, "weeks": ['
            '{"week": N, "posts": [{"day": "Monday", "format": "reel", '
            '"topic": "...", "objective": "reach", "caption_hint": "..."}]}'
            "]}"
        )
        try:
            raw = self._call_anthropic(prompt, system, max_tokens=2000)
            data = json.loads(raw)
            return {"ok": True, "data": data}
        except json.JSONDecodeError:
            return {"ok": True, "data": {"raw": raw}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _call_anthropic(self, prompt: str, system: str, max_tokens: int = 2000) -> str:
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
