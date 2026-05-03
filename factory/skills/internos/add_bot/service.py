"""Service for add_bot - creates Telegram bots for Factory."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from templates import bot_md, bot_py, manifest_json, tools_py

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_VALID_BOT_TYPES = {"admin", "client", "internal"}
_DEFAULT_COMMANDS = ["start", "ayuda", "crear_agente", "skills", "empresa", "salir"]


class AddBotService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        if context.get("dry_run", True):
            return self._planear(context)

        return self._crear(context)

    # --- validacion ---

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        bot_name = context.get("bot_name")
        if not bot_name:
            return False, "bot_name es requerido"
        if not isinstance(bot_name, str):
            return False, "bot_name debe ser texto"
        if not _NAME_PATTERN.match(bot_name):
            return False, "bot_name debe estar en snake_case y empezar con letra"
        bot_type = context.get("bot_type", "admin")
        if bot_type not in _VALID_BOT_TYPES:
            return False, f"bot_type debe ser uno de: {', '.join(sorted(_VALID_BOT_TYPES))}"
        token_env = context.get("token_env")
        if not token_env:
            return False, "token_env es requerido"
        if not isinstance(token_env, str):
            return False, "token_env debe ser texto"
        if "TOKEN" not in token_env.upper():
            return False, "token_env debe apuntar a una variable de token"
        admin_chat_id = context.get("admin_chat_id")
        if admin_chat_id is not None and not isinstance(admin_chat_id, (str, int)):
            return False, "admin_chat_id debe ser texto o numero"
        commands = context.get("commands", [])
        if commands and not isinstance(commands, (list, str)):
            return False, "commands debe ser lista o texto separado por comas"
        if not isinstance(context.get("dry_run", True), bool):
            return False, "dry_run debe ser booleano"
        return True, None

    # --- scaffold ---

    def _planear(self, context: dict) -> dict:
        bot_path = self._bot_path(context)
        commands = self._parse_commands(context.get("commands"))
        return {
            "ok": True,
            "message": "plan de bot generado; no se escribio nada",
            "data": {
                "bot_name": context["bot_name"],
                "bot_type": context.get("bot_type", "admin"),
                "bot_path": str(bot_path),
                "exists": bot_path.exists(),
                "token_env": context["token_env"],
                "admin_chat_id": str(context.get("admin_chat_id", "")),
                "empresa": context.get("empresa", "factory"),
                "commands": commands,
                "files": [str(bot_path / f) for f in ("BOT.md", "manifest.json", "bot.py", "config.json", "tools.py")],
            },
        }

    def _crear(self, context: dict) -> dict:
        plan = self._planear(context)
        data = plan["data"]
        if data["exists"]:
            return {"ok": False, "error": f"bot ya existe: {data['bot_path']}", "data": data}

        self._load_env()
        token = os.getenv(data["token_env"])
        if not token:
            return {"ok": False, "error": f"variable de entorno no encontrada: {data['token_env']}"}

        token_check = self._telegram_get_me(token)
        if not token_check["ok"]:
            return token_check

        bot_path = Path(data["bot_path"])
        self._escribir_archivos(bot_path, data, token_check["data"])
        registry_result = self._registrar(context, data, token_check["data"])
        ready_result = self._send_ready_message(token, data)

        return {
            "ok": True,
            "message": "bot creado y registrado",
            "data": {
                **data,
                "telegram_bot": token_check["data"],
                "registry": registry_result["data"],
                "ready_message": ready_result,
            },
        }

    def _escribir_archivos(self, bot_path: Path, data: dict, telegram_bot: dict) -> None:
        bot_path.mkdir(parents=True, exist_ok=True)
        config = {
            "bot_name": data["bot_name"],
            "bot_type": data["bot_type"],
            "empresa": data["empresa"],
            "token_env": data["token_env"],
            "admin_chat_id": data["admin_chat_id"],
            "telegram_username": telegram_bot.get("username", ""),
            "commands": data["commands"],
        }
        bot_path.joinpath("BOT.md").write_text(bot_md.render(data, telegram_bot), encoding="utf-8")
        bot_path.joinpath("manifest.json").write_text(manifest_json.render(data, telegram_bot), encoding="utf-8")
        bot_path.joinpath("bot.py").write_text(bot_py.render(), encoding="utf-8")
        bot_path.joinpath("config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        bot_path.joinpath("tools.py").write_text(tools_py.render(data["commands"]), encoding="utf-8")

    # --- registry ---

    def _registrar(self, context: dict, data: dict, telegram_bot: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        registry_path = base_dir / "bots" / "registry.json"
        registry = self._load_registry(registry_path)
        entry = {
            "nombre": data["bot_name"],
            "bot_type": data["bot_type"],
            "empresa": data["empresa"],
            "path": f"bots/{data['bot_name']}",
            "entrypoint": "bot.py",
            "token_env": data["token_env"],
            "admin_chat_id": data["admin_chat_id"],
            "telegram_username": telegram_bot.get("username", ""),
            "commands": data["commands"],
            "version": "0.1.0",
        }
        registry[data["bot_name"]] = entry
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "data": {"registry_path": str(registry_path), "entry": entry}}

    def _load_registry(self, registry_path: Path) -> dict:
        if not registry_path.exists():
            return {}
        raw = registry_path.read_text(encoding="utf-8", errors="replace").strip()
        return json.loads(raw) if raw else {}

    # --- telegram ---

    def _telegram_get_me(self, token: str) -> dict:
        result = self._telegram_request(token, "getMe")
        if not result.get("ok"):
            return {"ok": False, "error": f"token Telegram invalido: {result}"}
        return {"ok": True, "data": result.get("result", {})}

    def _send_ready_message(self, token: str, data: dict) -> dict:
        chat_id = data.get("admin_chat_id")
        if not chat_id:
            return {"ok": False, "skipped": True, "error": "admin_chat_id no configurado"}
        return self._telegram_request(
            token, "sendMessage", {"chat_id": chat_id, "text": f"ready to work, soy {data['bot_name']}"}
        )

    def _telegram_request(self, token: str, method: str, params: dict | None = None) -> dict:
        url = f"https://api.telegram.org/bot{token}/{method}"
        data = urllib.parse.urlencode(params).encode("utf-8") if params else None
        try:
            with urllib.request.urlopen(url, data=data, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # --- helpers ---

    def _load_env(self) -> None:
        env_path = Path(".env")
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

    def _parse_commands(self, raw) -> list[str]:
        if not raw:
            return _DEFAULT_COMMANDS
        if isinstance(raw, str):
            return [item.strip().lstrip("/") for item in raw.split(",") if item.strip()]
        return [str(item).strip().lstrip("/") for item in raw if str(item).strip()]

    def _bot_path(self, context: dict) -> Path:
        base_dir = Path(context.get("base_dir", "factory"))
        return base_dir / "bots" / context["bot_name"]
