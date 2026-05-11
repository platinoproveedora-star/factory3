"""Genera documentación markdown de un skill desde manifest + service.py sin IA."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_FOLDERS     = ["internos", "meta", "eval"]


class SkillDocGeneratorService:

    def ejecutar(self, context: dict) -> dict:
        skill_name = (context.get("skill_name") or "").strip()
        source     = (context.get("source") or "").strip()

        if not skill_name:
            return {"ok": False, "error": "skill_name requerido"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        skill_path = self._resolver(skill_name, source)
        if not skill_path:
            return {"ok": False, "error": f"skill '{skill_name}' no encontrado"}

        manifest = self._leer_manifest(skill_path)
        service_info = self._analizar_service(skill_path)
        doc = self._generar_doc(skill_name, manifest, service_info)

        return {
            "ok": True,
            "message": f"doc generada: {skill_name}",
            "data": {
                "skill_name": skill_name,
                "markdown":   doc,
                "manifest":   manifest,
                "service_info": service_info,
            },
        }

    def _resolver(self, name: str, source: str) -> Path | None:
        if source:
            folders = [source] if source in _FOLDERS else _FOLDERS
        else:
            folders = _FOLDERS
        for folder in folders:
            p = _SKILLS_ROOT / folder / name
            if p.exists():
                return p
        return None

    def _leer_manifest(self, skill_path: Path) -> dict:
        m = skill_path / "manifest.json"
        if not m.exists():
            return {}
        try:
            return json.loads(m.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _analizar_service(self, skill_path: Path) -> dict:
        svc = skill_path / "service.py"
        if not svc.exists():
            return {}
        code = svc.read_text(encoding="utf-8", errors="replace")
        info = {"docstring": "", "clase": "", "metodos": [], "env_vars": [], "lineas": len(code.splitlines())}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    info["clase"] = node.name
                    if (ast.get_docstring(node)):
                        info["docstring"] = ast.get_docstring(node)
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            args = [a.arg for a in item.args.args if a.arg != "self"]
                            doc  = ast.get_docstring(item) or ""
                            info["metodos"].append({"nombre": item.name, "args": args, "doc": doc})
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "getenv":
                        for a in node.args:
                            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                                if a.value not in info["env_vars"]:
                                    info["env_vars"].append(a.value)
        except SyntaxError:
            pass
        if not info["docstring"]:
            m = re.match(r'"""(.+?)"""', code, re.DOTALL)
            if m:
                info["docstring"] = m.group(1).strip()
        return info

    def _generar_doc(self, nombre: str, manifest: dict, svc: dict) -> str:
        lines = [f"# {nombre}", ""]
        desc = manifest.get("description") or svc.get("docstring") or ""
        if desc:
            lines += [desc, ""]

        lines += ["## Info", ""]
        lines += [f"- **Tipo:** `{manifest.get('type', '?')}`"]
        lines += [f"- **Kind:** `{manifest.get('kind', '?')}`"]
        lines += [f"- **Version:** `{manifest.get('version', '0.1.0')}`"]
        lines += [f"- **Entrypoint:** `{manifest.get('entrypoint', 'skill.py')}`"]
        env = manifest.get("requires_env") or svc.get("env_vars") or []
        if env:
            lines += [f"- **Env vars:** `{', '.join(env)}`"]
        lines += [""]

        metodos_pub = [m for m in svc.get("metodos", []) if not m["nombre"].startswith("_")]
        if metodos_pub:
            lines += ["## Métodos públicos", ""]
            for m in metodos_pub:
                args_str = ", ".join(m["args"])
                lines += [f"### `{m['nombre']}({args_str})`"]
                if m["doc"]:
                    lines += [m["doc"]]
                lines += [""]

        lines += ["## Uso", ""]
        lines += ["```python"]
        clase = svc.get("clase") or "".join(p.capitalize() for p in nombre.split("_")) + "Service"
        lines += [f"from service import {clase}", ""]
        lines += [f'result = {clase}().ejecutar({{']
        lines += [f'    # context params aquí']
        lines += [f'}})']
        lines += ["```", ""]

        lines += ["## Contrato de retorno", ""]
        lines += ["```python"]
        lines += ['# Éxito']
        lines += ['{"ok": True, "message": "...", "data": {...}}']
        lines += ['# Error']
        lines += ['{"ok": False, "error": "mensaje descriptivo"}']
        lines += ["```"]

        return "\n".join(lines)
