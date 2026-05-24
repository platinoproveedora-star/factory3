"""Service for buyer_persona_generator - creates detailed buyer personas."""

from __future__ import annotations

import json
import os
import urllib.request


class BuyerPersonaGeneratorService:

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
        for field in ("negocio", "producto", "mercado"):
            if not context.get(field):
                return False, f"{field} es requerido"
        num = context.get("num_personas", 2)
        if not isinstance(num, int) or num < 1 or num > 5:
            return False, "num_personas debe ser entre 1 y 5"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        negocio = context["negocio"]
        producto = context["producto"]
        mercado = context["mercado"]
        num = context.get("num_personas", 2)

        system = (
            "Eres un experto en marketing estratégico y segmentación de mercados. "
            "Creas buyer personas detalladas y accionables basadas en datos reales. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"Crea {num} buyer personas para:\n"
            f"Negocio: {negocio}\n"
            f"Producto: {producto}\n"
            f"Mercado: {mercado}\n\n"
            "Devuelve JSON:\n"
            '{"personas": [{"nombre": "...", "edad": "...", "ocupacion": "...", "ingreso": "...", '
            '"metas": [...], "dolores": [...], "objeciones": [...], "canales_preferidos": [...], '
            '"frase_tipica": "...", "como_convencerlo": "..."}]}'
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
