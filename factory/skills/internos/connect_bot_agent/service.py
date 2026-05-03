"""Service for connect_bot_agent - links bots to default agents."""

from __future__ import annotations

import json
import re
from pathlib import Path

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
_VALID_MODES = {"chat", "default"}


class ConnectBotAgentService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error, "data": {"received_context": context}}

        plan = self._planear(context)
        if not plan["ok"] or context.get("dry_run", True):
            return plan

        return self._conectar(context, plan["data"])

    # --- validacion ---

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        bot_name = context.get("bot_name")
        agent_name = context.get("agent_name")
        if not bot_name:
            return False, "bot_name es requerido"
        if not agent_name:
            return False, "agent_name es requerido"
        if not isinstance(bot_name, str):
            return False, "bot_name debe ser texto"
        if not isinstance(agent_name, str):
            return False, "agent_name debe ser texto"
        if not _VALID_NAME.match(bot_name):
            return False, "bot_name debe iniciar con letra y usar letras, numeros, _ o -"
        if not _VALID_NAME.match(agent_name):
            return False, "agent_name debe iniciar con letra y usar letras, numeros, _ o -"
        mode = context.get("mode", "chat")
        if mode not in _VALID_MODES:
            return False, f"mode debe ser uno de: {', '.join(sorted(_VALID_MODES))}"
        if not isinstance(context.get("dry_run", True), bool):
            return False, "dry_run debe ser booleano"
        return True, None

    # --- plan ---

    def _planear(self, context: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        bot_name = context["bot_name"]
        agent_name = context["agent_name"]
        mode = context.get("mode", "chat")

        bots_registry_path = base_dir / "bots" / "registry.json"
        agents_registry_path = base_dir / "agents" / "registry.json"
        bots_registry = self._load_json(bots_registry_path)
        agents_registry = self._load_json(agents_registry_path)

        bot_entry = bots_registry.get(bot_name)
        if not isinstance(bot_entry, dict):
            return {"ok": False, "error": f"bot no registrado: {bot_name}"}

        agent_entry = agents_registry.get(agent_name)
        if not isinstance(agent_entry, dict):
            return {"ok": False, "error": f"agente no registrado: {agent_name}"}

        bot_path = base_dir / bot_entry.get("path", f"bots/{bot_name}")
        agent_path = base_dir / agent_entry.get("path", f"agents/{agent_name}")
        bot_config_path = bot_path / "config.json"
        bot_manifest_path = bot_path / "manifest.json"

        missing = [
            str(path)
            for path in (bot_path, agent_path, bot_config_path)
            if not path.exists()
        ]
        if missing:
            return {"ok": False, "error": "faltan paths requeridos", "data": {"missing": missing}}

        connection = {
            "default_agent": agent_name,
            "mode": mode,
            "agent_path": agent_entry.get("path", f"agents/{agent_name}"),
        }
        return {
            "ok": True,
            "message": "plan de conexion generado; no se escribio nada",
            "data": {
                "bot_name": bot_name,
                "agent_name": agent_name,
                "mode": mode,
                "bot_path": str(bot_path),
                "agent_path": str(agent_path),
                "bot_config_path": str(bot_config_path),
                "bot_manifest_path": str(bot_manifest_path),
                "bots_registry_path": str(bots_registry_path),
                "connection": connection,
            },
        }

    # --- write ---

    def _conectar(self, context: dict, data: dict) -> dict:
        bot_config_path = Path(data["bot_config_path"])
        bot_manifest_path = Path(data["bot_manifest_path"])
        bots_registry_path = Path(data["bots_registry_path"])
        bot_name = data["bot_name"]
        connection = data["connection"]

        config = self._load_json(bot_config_path)
        config["default_agent"] = connection["default_agent"]
        config["agent"] = {
            "default": connection["default_agent"],
            "mode": connection["mode"],
        }
        self._write_json(bot_config_path, config)

        if bot_manifest_path.exists():
            manifest = self._load_json(bot_manifest_path)
        else:
            manifest = {}
        manifest["agent"] = {
            "default": connection["default_agent"],
            "mode": connection["mode"],
        }
        self._write_json(bot_manifest_path, manifest)

        bots_registry = self._load_json(bots_registry_path)
        bots_registry[bot_name]["default_agent"] = connection["default_agent"]
        bots_registry[bot_name]["agent"] = {
            "default": connection["default_agent"],
            "mode": connection["mode"],
        }
        self._write_json(bots_registry_path, bots_registry)

        return {
            "ok": True,
            "message": "bot conectado al agente",
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
