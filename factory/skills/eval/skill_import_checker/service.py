"""Lee service.py de un skill y verifica que todos los imports estén disponibles."""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_FOLDERS     = ["internos", "meta", "eval"]

# Módulos que sabemos que son locales (relativos al skill) — no intentar importar
_LOCAL_MODULES = {"service", "templates", "skill"}


class SkillImportCheckerService:

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

        service_file = skill_path / "service.py"
        if not service_file.exists():
            return {"ok": False, "error": "service.py no encontrado"}

        code    = service_file.read_text(encoding="utf-8", errors="replace")
        imports = self._extraer_imports(code)
        checks  = self._verificar(imports)

        faltantes  = [c for c in checks if not c["disponible"] and c["tipo"] == "stdlib_o_externo"]
        warnings   = [c for c in checks if not c["disponible"] and c["tipo"] == "local"]
        todo_ok    = len(faltantes) == 0

        return {
            "ok": todo_ok,
            "message": (
                f"{'OK' if todo_ok else f'{len(faltantes)} imports faltantes'} — "
                f"{len(checks)} imports analizados"
            ),
            "data": {
                "skill_name":  skill_name,
                "ok":          todo_ok,
                "faltantes":   len(faltantes),
                "warnings":    len(warnings),
                "total":       len(checks),
                "imports":     checks,
            },
        }

    def _extraer_imports(self, code: str) -> list[dict]:
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({"modulo": alias.name.split(".")[0], "linea": node.lineno, "from": False})
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append({"modulo": node.module.split(".")[0], "linea": node.lineno, "from": True})
        except SyntaxError:
            pass
        # deduplicar por módulo
        seen = set()
        unique = []
        for imp in imports:
            if imp["modulo"] not in seen:
                seen.add(imp["modulo"])
                unique.append(imp)
        return unique

    def _verificar(self, imports: list[dict]) -> list[dict]:
        checks = []
        for imp in imports:
            modulo = imp["modulo"]
            if modulo in _LOCAL_MODULES:
                checks.append({**imp, "disponible": True, "tipo": "local",
                                "nota": "módulo local del skill"})
                continue
            if modulo.startswith("_"):
                checks.append({**imp, "disponible": True, "tipo": "interno_python",
                                "nota": "módulo interno Python"})
                continue
            try:
                importlib.import_module(modulo)
                disponible = True
                nota = "disponible"
            except ImportError:
                disponible = False
                nota = "NO instalado"
            except Exception as e:
                disponible = True
                nota = f"importable con advertencia: {e}"

            checks.append({**imp, "disponible": disponible,
                            "tipo": "stdlib_o_externo", "nota": nota})
        return checks

    def _resolver(self, name: str, source: str) -> Path | None:
        if source and source in _FOLDERS:
            p = _SKILLS_ROOT / source / name
            if p.exists():
                return p
        for folder in _FOLDERS:
            p = _SKILLS_ROOT / folder / name
            if p.exists():
                return p
        return None
