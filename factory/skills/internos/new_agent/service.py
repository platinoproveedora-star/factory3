"""Service for new_agent - creates portable agent structures."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from templates import agent_brain_py, agent_py, manifest_json, service_py, skill_md, system_md

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
_VALID_TABLE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_TRUE_VALUES = {"1", "true", "t", "yes", "y", "si", "s\u00ed", "s", "on"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off", ""}


class NewAgentService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error, "data": {"received_context": context}}

        if context.get("dry_run", True):
            return self._planear(context)

        if context.get("to_files"):
            return self._generar_contenido(context)

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
        if not isinstance(context.get("mcps", ""), str):
            return False, "mcps debe ser texto separado por comas"
        if not isinstance(context.get("skills", ""), str):
            return False, "skills debe ser texto separado por comas"
        if not isinstance(context.get("vertical", "general"), str):
            return False, "vertical debe ser texto"
        if not isinstance(context.get("descripcion", ""), str):
            return False, "descripcion debe ser texto"
        memory_value, memory_error = self._memory_enabled(context)
        if memory_error:
            return False, memory_error
        table_name = context.get("memory_table") or context.get("table_name") or "agent_memory"
        if memory_value and (not isinstance(table_name, str) or not _VALID_TABLE_NAME.match(table_name)):
            return False, "memory_table debe ser snake_case"
        agent_id = context.get("agent_id")
        if agent_id:
            if not isinstance(agent_id, str):
                return False, "agent_id debe ser texto"
            try:
                uuid.UUID(agent_id)
            except ValueError:
                return False, "agent_id debe ser UUID valido"
        return True, None

    # --- scaffold ---

    def _planear(self, context: dict) -> dict:
        agent_path = self._agent_path(context)
        nombre = context["nombre"]
        agent_id = context.get("agent_id") or str(uuid.uuid4())
        mcps = self._split_csv(context.get("mcps", ""))
        skills = self._split_csv(context.get("skills", ""))
        memory = self._memory_metadata(context, nombre)
        next_steps = []
        if memory:
            next_steps.append(
                {
                    "skill": "add_agent_memory_supabase",
                    "context": {
                        "agent_name": nombre,
                        "table_name": memory["table"],
                        "base_dir": context.get("base_dir", "factory"),
                        "dry_run": True,
                    },
                }
            )
        return {
            "ok": True,
            "message": "plan de agente generado; no se escribio nada",
            "data": {
                "nombre": nombre,
                "agent_id": agent_id,
                "agent_path": str(agent_path),
                "directories": [str(agent_path)],
                "files": [str(agent_path / f) for f in ("SKILL.md", "manifest.json", "agent.py", "service.py")],
                "exists": agent_path.exists(),
                "mcps": mcps,
                "skills": skills,
                "memory": memory,
                "next_steps": next_steps,
            },
        }

    def _generar_contenido(self, context: dict) -> dict:
        plan = self._planear(context)
        data = plan["data"]
        nombre = context["nombre"]
        descripcion = context.get("descripcion") or f"Agente {nombre}"
        vertical = context.get("vertical", "general")
        base_dir = context.get("base_dir", "factory")

        files = [
            {"path": f"{base_dir}/agents/{nombre}/SKILL.md", "content": skill_md.render(nombre, data["agent_id"], vertical, descripcion, data["mcps"], data["skills"])},
            {"path": f"{base_dir}/agents/{nombre}/manifest.json", "content": manifest_json.render(nombre, data["agent_id"], vertical, descripcion, data["mcps"], data["skills"], data["memory"])},
            {"path": f"{base_dir}/agents/{nombre}/agent.py", "content": agent_py.render()},
            {"path": f"{base_dir}/agents/{nombre}/service.py", "content": service_py.render(nombre, data["agent_id"], descripcion, data["mcps"], data["skills"])},
            {"path": f"{base_dir}/agents/{nombre}/agent_brain.py", "content": agent_brain_py.render()},
            {"path": f"{base_dir}/agents/{nombre}/prompts/system.md", "content": system_md.render(nombre, descripcion)},
        ]

        registry_entry = {
            "agent_id": data["agent_id"],
            "nombre": nombre,
            "descripcion": descripcion,
            "vertical": vertical,
            "mcps": data["mcps"],
            "skills": data["skills"],
            "path": f"agents/{nombre}",
            "entrypoint": "agent.py",
            "version": "0.1.0",
        }
        if data["memory"]:
            registry_entry["memory"] = data["memory"]
        registry_path = Path(base_dir) / "agents" / "registry.json"
        existing_registry = self._load_registry(registry_path)
        existing_registry[nombre] = registry_entry
        files.append({
            "path": f"{base_dir}/agents/registry.json",
            "content": json.dumps(existing_registry, indent=2, ensure_ascii=False),
        })

        return {
            "ok": True,
            "message": "contenido de agente generado sin escribir en disco",
            "data": {"nombre": nombre, "agent_id": data["agent_id"], "files": files},
        }

    def _crear_archivos(self, context: dict) -> dict:
        plan = self._planear(context)
        data = plan["data"]
        agent_path = Path(data["agent_path"])
        nombre = context["nombre"]
        descripcion = context.get("descripcion") or f"Agente {nombre}"
        vertical = context.get("vertical", "general")

        if data["exists"]:
            return {"ok": False, "error": f"el agente ya existe: {agent_path}", "data": data}

        agent_path.mkdir(parents=True, exist_ok=True)
        (agent_path / "prompts").mkdir(exist_ok=True)

        files = {
            agent_path / "SKILL.md": skill_md.render(
                nombre,
                data["agent_id"],
                vertical,
                descripcion,
                data["mcps"],
                data["skills"],
            ),
            agent_path / "manifest.json": manifest_json.render(
                nombre,
                data["agent_id"],
                vertical,
                descripcion,
                data["mcps"],
                data["skills"],
                data["memory"],
            ),
            agent_path / "agent.py": agent_py.render(),
            agent_path / "service.py": service_py.render(
                nombre,
                data["agent_id"],
                descripcion,
                data["mcps"],
                data["skills"],
            ),
            agent_path / "agent_brain.py": agent_brain_py.render(),
            agent_path / "prompts" / "system.md": system_md.render(nombre, descripcion),
        }
        for path, content in files.items():
            path.write_text(content, encoding="utf-8")

        return {
            "ok": True,
            "message": "archivos de agente creados",
            "data": {
                "nombre": nombre,
                "agent_id": data["agent_id"],
                "agent_path": str(agent_path),
                "mcps": data["mcps"],
                "skills": data["skills"],
                "memory": data["memory"],
                "next_steps": data["next_steps"],
            },
        }

    # --- registry ---

    def _registrar(self, context: dict, scaffold_data: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        registry_path = base_dir / "agents" / "registry.json"
        nombre = context["nombre"]

        registry = self._load_registry(registry_path)
        entry = {
            "agent_id": scaffold_data["agent_id"],
            "nombre": nombre,
            "descripcion": context.get("descripcion", ""),
            "vertical": context.get("vertical", "general"),
            "mcps": scaffold_data["mcps"],
            "skills": scaffold_data["skills"],
            "path": f"agents/{nombre}",
            "entrypoint": "agent.py",
            "version": "0.1.0",
        }
        if scaffold_data["memory"]:
            entry["memory"] = scaffold_data["memory"]
        registry[nombre] = entry
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "ok": True,
            "message": "agente creado y registrado",
            "data": {
                "agent_id": scaffold_data["agent_id"],
                "agent_path": scaffold_data["agent_path"],
                "mcps": scaffold_data["mcps"],
                "skills": scaffold_data["skills"],
                "memory": scaffold_data["memory"],
                "next_steps": scaffold_data["next_steps"],
                "registry": {"registry_path": str(registry_path), "entry": entry},
            },
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

    def _agent_path(self, context: dict) -> Path:
        base_dir = Path(context.get("base_dir", "factory"))
        return base_dir / "agents" / context["nombre"]

    def _split_csv(self, value: str) -> list[str]:
        return [part.strip() for part in value.split(",") if part.strip()]

    def _memory_enabled(self, context: dict) -> tuple[bool, str | None]:
        for key in ("memory", "memoria", "use_memory"):
            if key not in context:
                continue
            value = context[key]
            if isinstance(value, bool):
                return value, None
            if isinstance(value, int):
                return value != 0, None
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in _TRUE_VALUES:
                    return True, None
                if normalized in _FALSE_VALUES:
                    return False, None
            return False, f"{key} debe ser boolean-ish"
        return False, None

    def _memory_metadata(self, context: dict, nombre: str) -> dict | None:
        enabled, _error = self._memory_enabled(context)
        if not enabled:
            return None
        table_name = context.get("memory_table") or context.get("table_name") or "agent_memory"
        return {
            "provider": "supabase",
            "table": table_name,
            "status": "pending_setup",
            "setup_skill": "add_agent_memory_supabase",
            "setup_context": {
                "agent_name": nombre,
                "table_name": table_name,
            },
            "requires_env": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"],
        }
