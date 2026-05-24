"""Service for campaign_planner - plans a complete marketing campaign."""

from __future__ import annotations

import json
import os
import urllib.request


class CampaignPlannerService:

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
        for field in ("objetivo", "producto", "audiencia"):
            if not context.get(field):
                return False, f"{field} es requerido"
        duracion = context.get("duracion_dias", 30)
        if not isinstance(duracion, int) or duracion < 1:
            return False, "duracion_dias debe ser un entero positivo"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        objetivo = context["objetivo"]
        producto = context["producto"]
        audiencia = context["audiencia"]
        duracion = context.get("duracion_dias", 30)
        presupuesto = context.get("presupuesto", "no definido")

        system = (
            "Eres un estratega de marketing digital senior. "
            "Creas planes de campaña completos y accionables. "
            "Responde SIEMPRE en JSON valido, sin texto adicional."
        )
        prompt = (
            f"Crea un plan de campaña de marketing:\n"
            f"Objetivo: {objetivo}\n"
            f"Producto: {producto}\n"
            f"Audiencia: {audiencia}\n"
            f"Duración: {duracion} días\n"
            f"Presupuesto: {presupuesto}\n\n"
            "Devuelve JSON con:\n"
            '{"nombre_campana": "...", "objetivo_smart": "...", "fases": [{"nombre": "...", "dias": "...", "acciones": [...]}], '
            '"canales": [...], "mensajes_clave": [...], "kpis": [...], "calendario_resumen": "..."}'
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
