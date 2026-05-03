"""Service for add_agent_brain - adds an Anthropic brain to an agent."""

from __future__ import annotations

import json
import re
from pathlib import Path

from templates import agent_brain_py, system_md

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
_VALID_PROVIDERS = {"anthropic"}
_DEFAULT_MODEL = "claude-3-5-haiku-latest"
_DEFAULT_PROMPT = "Eres un agente de Factory. Responde de forma clara, breve y util."


class AddAgentBrainService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error, "data": {"received_context": context}}

        plan = self._planear(context)
        if not plan["ok"] or context.get("dry_run", True):
            return plan

        return self._crear_brain(context, plan["data"])

    # --- validacion ---

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        agent_name = context.get("agent_name")
        if not agent_name:
            return False, "agent_name es requerido"
        if not isinstance(agent_name, str):
            return False, "agent_name debe ser texto"
        if not _VALID_NAME.match(agent_name):
            return False, "agent_name debe iniciar con letra y usar letras, numeros, _ o -"
        provider = context.get("provider", "anthropic")
        if provider not in _VALID_PROVIDERS:
            return False, f"provider debe ser uno de: {', '.join(sorted(_VALID_PROVIDERS))}"
        if not isinstance(context.get("model", _DEFAULT_MODEL), str):
            return False, "model debe ser texto"
        if not isinstance(context.get("system_prompt", _DEFAULT_PROMPT), str):
            return False, "system_prompt debe ser texto"
        if not isinstance(context.get("dry_run", True), bool):
            return False, "dry_run debe ser booleano"
        return True, None

    # --- plan ---

    def _planear(self, context: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        agent_name = context["agent_name"]
        provider = context.get("provider", "anthropic")
        model = context.get("model", _DEFAULT_MODEL)
        prompt = context.get("system_prompt", _DEFAULT_PROMPT)

        agents_registry_path = base_dir / "agents" / "registry.json"
        agents_registry = self._load_json(agents_registry_path)
        agent_entry = agents_registry.get(agent_name)
        if not isinstance(agent_entry, dict):
            return {"ok": False, "error": f"agente no registrado: {agent_name}"}

        agent_path = base_dir / agent_entry.get("path", f"agents/{agent_name}")
        manifest_path = agent_path / "manifest.json"
        skill_md_path = agent_path / "SKILL.md"
        brain_path = agent_path / "agent_brain.py"
        prompt_path = agent_path / "prompts" / "system.md"

        missing = [
            str(path)
            for path in (agent_path, manifest_path)
            if not path.exists()
        ]
        if missing:
            return {"ok": False, "error": "faltan paths requeridos", "data": {"missing": missing}}

        brain = {
            "provider": provider,
            "model": model,
            "entrypoint": "agent_brain.py",
            "system_prompt": "prompts/system.md",
            "requires_env": ["ANTHROPIC_API_KEY"],
        }
        return {
            "ok": True,
            "message": "plan de brain generado; no se escribio nada",
            "data": {
                "agent_name": agent_name,
                "agent_path": str(agent_path),
                "manifest_path": str(manifest_path),
                "skill_md_path": str(skill_md_path),
                "brain_path": str(brain_path),
                "prompt_path": str(prompt_path),
                "brain": brain,
                "system_prompt": prompt,
                "exists": {
                    "agent_brain": brain_path.exists(),
                    "system_prompt": prompt_path.exists(),
                },
            },
        }

    # --- write ---

    def _crear_brain(self, context: dict, data: dict) -> dict:
        agent_name = data["agent_name"]
        manifest_path = Path(data["manifest_path"])
        skill_md_path = Path(data["skill_md_path"])
        brain_path = Path(data["brain_path"])
        prompt_path = Path(data["prompt_path"])
        brain = data["brain"]

        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        brain_path.write_text(agent_brain_py.render(brain["model"]), encoding="utf-8")
        prompt_path.write_text(system_md.render(agent_name, data["system_prompt"]), encoding="utf-8")

        manifest = self._load_json(manifest_path)
        manifest["brain"] = brain
        requires_env = set(manifest.get("requires_env", []))
        requires_env.update(brain["requires_env"])
        manifest["requires_env"] = sorted(requires_env)
        self._write_json(manifest_path, manifest)

        if skill_md_path.exists():
            skill_md = skill_md_path.read_text(encoding="utf-8", errors="replace")
            marker = "## Brain"
            if marker not in skill_md:
                skill_md = skill_md.rstrip() + (
                    "\n\n## Brain\n\n"
                    f"- Provider: {brain['provider']}\n"
                    f"- Model: {brain['model']}\n"
                    f"- Entrypoint: `{brain['entrypoint']}`\n"
                    f"- System prompt: `{brain['system_prompt']}`\n"
                )
                skill_md_path.write_text(skill_md + "\n", encoding="utf-8")

        return {
            "ok": True,
            "message": "brain agregado al agente",
            "data": data,
        }

    # --- helpers ---

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
