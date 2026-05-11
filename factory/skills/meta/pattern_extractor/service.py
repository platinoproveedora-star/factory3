"""Detecta patrones repetitivos/automatizables en los pasos de un proceso."""
from __future__ import annotations

import json
import os
import urllib.request


class PatternExtractorService:

    def ejecutar(self, context: dict) -> dict:
        pasos = context.get("pasos") or []
        proceso_nombre = (context.get("proceso_nombre") or "proceso").strip()

        if not pasos:
            return {"ok": False, "error": "pasos requerido — lista de pasos del proceso"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        pasos_str = json.dumps(pasos, ensure_ascii=False, indent=2)
        prompt = (
            f"Analiza estos pasos del proceso '{proceso_nombre}' e identifica patrones:\n\n"
            f"{pasos_str}\n\n"
            f"Para cada patrón identificado, clasifícalo. Devuelve SOLO JSON válido:\n"
            f'{{"patrones": [{{'
            f'"tipo": "repetitivo|decision|transformacion|consulta|notificacion", '
            f'"nombre": "snake_case", '
            f'"descripcion": "1 línea", '
            f'"pasos_involucrados": [1, 2], '
            f'"automatizable": true, '
            f'"complejidad": "baja|media|alta", '
            f'"skill_sugerido": "snake_case o null"'
            f'}}]}}'
        )
        raw = self._llamar_haiku(prompt)
        if not raw:
            return {"ok": False, "error": "error al llamar Haiku"}

        try:
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            data  = json.loads(raw[start:end])
        except Exception as e:
            return {"ok": False, "error": f"JSON inválido: {e}"}

        patrones = data.get("patrones", [])
        automatizables = [p for p in patrones if p.get("automatizable")]
        return {
            "ok": True,
            "message": f"{len(patrones)} patrones, {len(automatizables)} automatizables",
            "data": data,
        }

    def _llamar_haiku(self, prompt: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return ""
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read().decode())
            return result.get("content", [{}])[0].get("text", "")
        except Exception:
            return ""
