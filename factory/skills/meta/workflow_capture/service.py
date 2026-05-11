"""Captura un proceso humano y lo convierte en pasos estructurados."""
from __future__ import annotations

import json
import os
import urllib.request


class WorkflowCaptureService:

    def ejecutar(self, context: dict) -> dict:
        proceso = (context.get("proceso") or "").strip()
        if not proceso:
            return {"ok": False, "error": "proceso requerido — describe el proceso en texto"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        prompt = (
            f"Analiza este proceso y conviértelo en pasos estructurados:\n\n{proceso}\n\n"
            f"Devuelve SOLO JSON válido:\n"
            f'{{"nombre_sugerido": "snake_case_corto", "descripcion": "1 línea", '
            f'"pasos": [{{"numero": 1, "accion": "verbo + objeto", '
            f'"input": "qué recibe", "output": "qué produce", "automatizable": true}}]}}'
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

        return {
            "ok": True,
            "message": f"{len(data.get('pasos', []))} pasos capturados",
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
