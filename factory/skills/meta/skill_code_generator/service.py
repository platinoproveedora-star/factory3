"""Genera service.py, skill.py y manifest.json reales a partir de una spec técnica."""
from __future__ import annotations

import json
import os
import urllib.request

_SONNET = "claude-sonnet-4-6"
_HAIKU  = "claude-haiku-4-5-20251001"

_SERVICE_EXAMPLE = '''
class EjemploService:

    def ejecutar(self, context: dict) -> dict:
        campo = (context.get("campo") or "").strip()
        if not campo:
            return {"ok": False, "error": "campo requerido"}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        resultado = self._procesar(campo)
        return {"ok": True, "message": "procesado", "data": {"resultado": resultado}}

    def _procesar(self, valor: str) -> str:
        return valor.upper()
'''.strip()

_SKILL_TEMPLATE = '''from __future__ import annotations
from service import {class_name}

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {{"ok": False, "error": "context debe ser dict"}}
    return {class_name}().ejecutar(context)
'''.strip()


class SkillCodeGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        spec = context.get("spec") or {}
        if not spec or not spec.get("skill_name"):
            return {"ok": False, "error": "spec requerida con campo 'skill_name'"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        model = _SONNET if context.get("use_sonnet", True) else _HAIKU
        service_code = self._generar_service(spec, model)
        if not service_code:
            return {"ok": False, "error": "error al llamar IA para generar código"}

        skill_name  = spec["skill_name"]
        class_name  = self._to_class_name(skill_name)
        skill_code  = _SKILL_TEMPLATE.format(class_name=class_name)
        manifest    = self._build_manifest(spec)

        return {
            "ok": True,
            "message": f"código generado: {skill_name}",
            "data": {
                "skill_name": skill_name,
                "service_py": service_code,
                "skill_py":   skill_code,
                "manifest_json": manifest,
            },
        }

    def _generar_service(self, spec: dict, model: str) -> str:
        skill_name   = spec["skill_name"]
        descripcion  = spec.get("descripcion", "")
        logica       = spec.get("logica_principal", "")
        params       = spec.get("context_params", [])
        outputs      = spec.get("output_fields", [])
        requiere_ia  = spec.get("requiere_ia", False)
        requiere_db  = spec.get("requiere_db", False)
        requires_env = spec.get("requires_env", [])
        casos_edge   = spec.get("casos_edge", [])

        params_str  = json.dumps(params,  ensure_ascii=False)
        outputs_str = json.dumps(outputs, ensure_ascii=False)
        edge_str    = json.dumps(casos_edge, ensure_ascii=False)

        ia_hint = ""
        if requiere_ia:
            ia_hint = (
                "\n- Usa claude-haiku-4-5-20251001 via urllib.request para la lógica de IA."
                "\n- El API key viene de os.getenv('ANTHROPIC_API_KEY')."
            )
        db_hint = ""
        if requiere_db:
            db_hint = (
                "\n- Para Supabase usa: from factory.engine import SupabaseClient; db = SupabaseClient(context)"
                "\n- Métodos: db.rest_select, db.rest_insert, db.rest_update, db.rest_delete"
            )

        prompt = f"""Genera el archivo service.py para un skill de Python llamado '{skill_name}'.

DESCRIPCIÓN: {descripcion}

LÓGICA PRINCIPAL (implementa exactamente esto):
{logica}

PARÁMETROS DE ENTRADA (context dict):
{params_str}

CAMPOS DE SALIDA EN data:
{outputs_str}

CASOS EDGE A MANEJAR:
{edge_str}

REGLAS OBLIGATORIAS:
- La clase se llama {self._to_class_name(skill_name)}
- Método principal: def ejecutar(self, context: dict) -> dict
- Siempre empieza con: from __future__ import annotations
- Retorno éxito: {{"ok": True, "message": "...", "data": {{...}}}}
- Retorno error: {{"ok": False, "error": "mensaje descriptivo"}}
- Soportar dry_run: if context.get("dry_run", False): return {{"ok": True, "message": "dry_run", "data": context}}
- Validar inputs requeridos al inicio
- NO usar print(), NO usar logging, NO usar argparse{ia_hint}{db_hint}

EJEMPLO DE ESTRUCTURA A SEGUIR:
{_SERVICE_EXAMPLE}

Devuelve ÚNICAMENTE el código Python, sin markdown, sin explicaciones, sin comentarios innecesarios."""

        return self._llamar_ia(prompt, model)

    def _llamar_ia(self, prompt: str, model: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return ""
        payload = {
            "model": model,
            "max_tokens": 3000,
            "messages": [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                result = json.loads(r.read().decode())
            text = result.get("content", [{}])[0].get("text", "")
            # strip markdown fences if model added them
            if "```python" in text:
                text = text.split("```python", 1)[1].split("```")[0]
            elif "```" in text:
                text = text.split("```", 1)[1].split("```")[0]
            return text.strip()
        except Exception:
            return ""

    def _to_class_name(self, skill_name: str) -> str:
        return "".join(p.capitalize() for p in skill_name.split("_")) + "Service"

    def _build_manifest(self, spec: dict) -> dict:
        return {
            "type": "skill",
            "name": spec["skill_name"],
            "version": "0.1.0",
            "kind": "executable",
            "entrypoint": "skill.py",
            "description": spec.get("descripcion", ""),
            "requires_env": spec.get("requires_env", []),
        }
