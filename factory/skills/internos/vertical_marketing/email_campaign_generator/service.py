"""Service for email_campaign_generator - generates email sequences."""

from __future__ import annotations

import json
import os
import urllib.request

_OBJETIVOS = {"nurture", "onboarding", "reactivacion", "venta"}


class EmailCampaignGeneratorService:

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
        if not context.get("producto"):
            return False, "producto es requerido"
        if not context.get("audiencia"):
            return False, "audiencia es requerido"
        if not context.get("objetivo") or context["objetivo"] not in _OBJETIVOS:
            return False, f"objetivo es requerido: {', '.join(sorted(_OBJETIVOS))}"
        num = context.get("num_emails", 5)
        if not isinstance(num, int) or num < 1 or num > 10:
            return False, "num_emails debe ser entre 1 y 10"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        producto = context["producto"]
        audiencia = context["audiencia"]
        objetivo = context["objetivo"]
        num_emails = context.get("num_emails", 5)

        system = (
            "Eres un experto en email marketing con alta tasa de apertura y conversión. "
            "Creas secuencias de emails que generan resultados. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"Crea una secuencia de {num_emails} emails:\n"
            f"Producto: {producto}\n"
            f"Audiencia: {audiencia}\n"
            f"Objetivo: {objetivo}\n\n"
            "Devuelve JSON:\n"
            '{"secuencia": [{"numero": 1, "dia_envio": 0, "asunto": "...", "preview": "...", "cuerpo": "...", "cta": "..."}]}'
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
            "max_tokens": 3000,
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
