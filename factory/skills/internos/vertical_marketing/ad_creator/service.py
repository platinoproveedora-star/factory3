"""Service for ad_creator - creates social media ads."""

from __future__ import annotations

import json
import os
import urllib.request

_PLATAFORMAS = {"facebook", "instagram", "google", "linkedin"}
_OBJETIVOS = {"trafico", "conversiones", "awareness"}


class AdCreatorService:

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
        if not context.get("plataforma") or context["plataforma"] not in _PLATAFORMAS:
            return False, f"plataforma es requerido: {', '.join(sorted(_PLATAFORMAS))}"
        if not context.get("producto"):
            return False, "producto es requerido"
        if not context.get("objetivo") or context["objetivo"] not in _OBJETIVOS:
            return False, f"objetivo es requerido: {', '.join(sorted(_OBJETIVOS))}"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        plataforma = context["plataforma"]
        producto = context["producto"]
        objetivo = context["objetivo"]
        presupuesto = context.get("presupuesto", "no definido")

        system = (
            "Eres un experto en publicidad digital con años de experiencia en Meta Ads y Google Ads. "
            "Creas anuncios de alto rendimiento optimizados por plataforma y objetivo. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"Crea un anuncio para:\n"
            f"Plataforma: {plataforma}\n"
            f"Producto: {producto}\n"
            f"Objetivo: {objetivo}\n"
            f"Presupuesto: {presupuesto}\n\n"
            "Devuelve JSON:\n"
            '{"headline": "...", "primary_text": "...", "description": "...", "cta": "...", '
            '"audiencia_sugerida": "...", "formato_recomendado": "...", "notas": "..."}'
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
