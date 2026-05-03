"""Service for ig_content_brief - generates Instagram content briefs by campaign objective."""
from __future__ import annotations

import json
import os
import urllib.request

_VALID_OBJECTIVES = {"reach", "engagement", "sales", "dms"}
_VALID_FORMATS = {"reel", "carousel", "story", "post"}


class IgContentBriefService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        objective = context.get("objective")
        if not objective:
            return False, "objective es requerido"
        if objective not in _VALID_OBJECTIVES:
            return False, f"objective debe ser uno de: {', '.join(sorted(_VALID_OBJECTIVES))}"
        if not context.get("topic") or not isinstance(context["topic"], str):
            return False, "topic es requerido y debe ser texto"
        fmt = context.get("format")
        if fmt is not None and fmt not in _VALID_FORMATS:
            return False, f"format debe ser uno de: {', '.join(sorted(_VALID_FORMATS))}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        objective = context["objective"]
        topic = context["topic"]
        target_audience = context.get("target_audience", "audiencia general")
        fmt = context.get("format", "reel")
        brand_voice = context.get("brand_voice", "")

        brand_line = f"Voz de marca: {brand_voice}\n" if brand_voice else ""
        objective_guides = {
            "reach": "hook amplio y contenido shareable, evitar demasiado nicho",
            "engagement": "pregunta al final, llamar a comentar o votar, incluir poll si es story",
            "sales": "prueba social, urgencia, beneficio claro y CTA directo a compra",
            "dms": "oferta exclusiva o promesa de respuesta personalizada, CTA a enviar DM",
        }
        system = (
            "Eres un estratega de contenido para Instagram. Generas briefs accionables para creadores y agentes. "
            "Responde SIEMPRE en JSON valido, sin texto adicional ni bloques de codigo."
        )
        prompt = (
            f"Genera un brief de contenido para Instagram:\n"
            f"Objetivo: {objective} ({objective_guides[objective]})\n"
            f"Tema: {topic}\n"
            f"Formato: {fmt}\n"
            f"Audiencia objetivo: {target_audience}\n"
            f"{brand_line}\n"
            "Devuelve unicamente este JSON:\n"
            '{"brief": {"objective": "...", "format": "...", "key_message": "...", '
            '"hook_suggestion": "...", "visual_direction": "...", "copy_notes": "...", '
            '"cta": "...", "kpis": [...], "do": [...], "dont": [...]}}'
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
