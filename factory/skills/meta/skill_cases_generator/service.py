"""Genera casos de prueba con input/output esperado a partir de una spec técnica."""
from __future__ import annotations

import json
import os
import urllib.request


class SkillCasesGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        spec = context.get("spec") or {}
        if not spec or not spec.get("skill_name"):
            return {"ok": False, "error": "spec requerida con campo 'skill_name'"}

        n_casos = int(context.get("n_casos", 5))
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        casos = self._generar_casos(spec, n_casos)
        if casos is None:
            return {"ok": False, "error": "error al llamar Haiku"}

        return {
            "ok": True,
            "message": f"{len(casos)} casos generados para {spec['skill_name']}",
            "data": {
                "skill_name": spec["skill_name"],
                "casos": casos,
            },
        }

    def _generar_casos(self, spec: dict, n: int) -> list | None:
        skill_name  = spec["skill_name"]
        descripcion = spec.get("descripcion", "")
        params      = spec.get("context_params", [])
        outputs     = spec.get("output_fields", [])
        casos_edge  = spec.get("casos_edge", [])
        test_input  = spec.get("test_input", {})

        params_str = json.dumps(params,     ensure_ascii=False)
        edge_str   = json.dumps(casos_edge, ensure_ascii=False)
        test_str   = json.dumps(test_input, ensure_ascii=False)

        prompt = (
            f"Genera {n} casos de prueba para el skill '{skill_name}'.\n\n"
            f"Descripción: {descripcion}\n"
            f"Parámetros: {params_str}\n"
            f"Casos edge conocidos: {edge_str}\n"
            f"Ejemplo de input: {test_str}\n\n"
            f"Incluye:\n"
            f"- 1 caso feliz (input válido completo, ok=true)\n"
            f"- 1 caso dry_run (dry_run=true, ok=true)\n"
            f"- casos de inputs inválidos/faltantes (ok=false)\n"
            f"- casos edge si aplica\n\n"
            f"Devuelve SOLO JSON válido:\n"
            f'[{{"nombre": "caso feliz", "tipo": "happy|dry_run|error|edge", '
            f'"input": {{}}, "expected_ok": true, "expected_fields": ["campo1"], '
            f'"descripcion": "qué verifica este caso"}}]'
        )
        raw = self._llamar_haiku(prompt)
        if not raw:
            return None
        try:
            start = raw.find("[")
            end   = raw.rfind("]") + 1
            return json.loads(raw[start:end])
        except Exception:
            return None

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
