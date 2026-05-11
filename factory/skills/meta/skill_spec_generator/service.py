"""Convierte un patrón automatizable en spec técnica para un skill factory3."""
from __future__ import annotations

import json
import os
import urllib.request


class SkillSpecGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        patron = context.get("patron") or {}
        proceso_contexto = (context.get("proceso_contexto") or "").strip()

        if not patron or not patron.get("nombre"):
            return {"ok": False, "error": "patron requerido con campo 'nombre'"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        patron_str = json.dumps(patron, ensure_ascii=False, indent=2)
        prompt = (
            f"Genera una spec técnica completa para un skill factory3 basado en este patrón:\n\n"
            f"{patron_str}\n\n"
            f"Contexto del proceso: {proceso_contexto or 'no especificado'}\n\n"
            f"Devuelve SOLO JSON válido con esta estructura exacta:\n"
            f'{{'
            f'"skill_name": "snake_case", '
            f'"descripcion": "1 línea clara", '
            f'"vertical": "rh|ventas|ops|meta|eval|general", '
            f'"context_params": [{{"nombre": "param", "tipo": "str|int|bool|list|dict", "requerido": true, "descripcion": "para qué sirve"}}], '
            f'"output_fields": [{{"campo": "nombre", "tipo": "str|int|bool|list|dict", "descripcion": "qué contiene"}}], '
            f'"requiere_ia": true, '
            f'"requiere_db": false, '
            f'"requires_env": ["ANTHROPIC_API_KEY"], '
            f'"logica_principal": "descripción en 3-5 pasos de qué hace el service.py", '
            f'"casos_edge": ["caso 1", "caso 2"], '
            f'"test_input": {{}}'
            f'}}'
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
            "message": f"spec generada: {data.get('skill_name', '?')}",
            "data": data,
        }

    def _llamar_haiku(self, prompt: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return ""
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 2048,
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
