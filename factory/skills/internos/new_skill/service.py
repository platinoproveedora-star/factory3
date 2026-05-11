"""Service for new_skill - creates portable skill structures."""

from __future__ import annotations

import json
import re
from pathlib import Path

from templates import manifest_json, service_py, skill_md, skill_py

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


class NewSkillService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error, "data": {"received_context": context}}

        if context.get("dry_run", True):
            return self._planear(context)

        scaffold_result = self._crear_archivos(context)
        if not scaffold_result["ok"]:
            return scaffold_result

        return self._registrar(context, scaffold_result["data"])

    # --- validacion ---

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        nombre = context.get("nombre")
        if not nombre:
            return False, "nombre es requerido"
        if not isinstance(nombre, str):
            return False, "nombre debe ser texto"
        if not _VALID_NAME.match(nombre):
            return False, "nombre debe iniciar con letra minuscula y usar solo letras, numeros, _ o -"
        if not isinstance(context.get("vertical", "general"), str):
            return False, "vertical debe ser texto"
        if not isinstance(context.get("descripcion", ""), str):
            return False, "descripcion debe ser texto"
        return True, None

    # --- scaffold ---

    def _planear(self, context: dict) -> dict:
        skill_path = self._skill_path(context)
        nombre = context["nombre"]
        return {
            "ok": True,
            "message": "plan de scaffold generado; no se escribio nada",
            "data": {
                "nombre": nombre,
                "skill_path": str(skill_path),
                "files": [str(skill_path / f) for f in ("SKILL.md", "manifest.json", "skill.py", "service.py")],
                "exists": skill_path.exists(),
            },
        }

    def _crear_archivos(self, context: dict) -> dict:
        skill_path = self._skill_path(context)
        nombre = context["nombre"]
        class_name = self._class_name(nombre)
        vertical = context.get("vertical", "general")
        descripcion = context.get("descripcion", f"Skill {nombre}")

        if skill_path.exists():
            return {"ok": False, "error": f"el skill ya existe: {skill_path}"}

        (skill_path / "templates").mkdir(parents=True, exist_ok=True)

        files = {
            skill_path / "SKILL.md": skill_md.render(nombre, vertical, descripcion),
            skill_path / "manifest.json": manifest_json.render(nombre, vertical, descripcion),
            skill_path / "skill.py": skill_py.render(class_name),
            skill_path / "service.py": context.get("service_py_override") or service_py.render(class_name),
        }
        for path, content in files.items():
            path.write_text(content, encoding="utf-8")

        return {
            "ok": True,
            "message": "archivos de skill creados",
            "data": {"nombre": nombre, "skill_path": str(skill_path), "class_name": class_name},
        }

    # --- registry ---

    def _registrar(self, context: dict, scaffold_data: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        registry_path = base_dir / "skills" / "registry.json"
        nombre = context["nombre"]

        registry = self._load_registry(registry_path)
        entry = {
            "tipo": "interno",
            "nombre": nombre,
            "vertical": context.get("vertical", "general"),
            "descripcion": context.get("descripcion", f"Skill {nombre}"),
            "path": f"skills/internos/{nombre}",
            "entrypoint": "skill.py",
            "version": "0.1.0",
        }
        registry[nombre] = entry
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "ok": True,
            "message": "skill creado y registrado",
            "data": {"scaffold": scaffold_data, "registry": {"path": str(registry_path), "entry": entry}},
        }

    def _load_registry(self, registry_path: Path) -> dict:
        if not registry_path.exists():
            return {}
        for encoding in ("utf-8", "utf-8-sig", "utf-16"):
            try:
                raw = registry_path.read_text(encoding=encoding).strip()
                return json.loads(raw) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return {}

    # --- helpers ---

    def _skill_path(self, context: dict) -> Path:
        base_dir = Path(context.get("base_dir", "factory"))
        return base_dir / "skills" / "internos" / context["nombre"]

    def _class_name(self, nombre: str) -> str:
        normalized = nombre.replace("-", "_")
        return "".join(part.capitalize() for part in normalized.split("_") if part)
