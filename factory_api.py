"""FastAPI webhook server for Factory bots."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request


BASE_DIR = Path(__file__).parent
FACTORY_DIR = BASE_DIR / "factory"

CONVERSATION_STATE: dict = {}


def load_env_file(path: Path = BASE_DIR / ".env") -> None:
    """Load local environment variables without printing secrets."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue

        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}

    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    return data if isinstance(data, dict) else {}


def telegram_request(token: str, method: str, params: dict | None = None) -> dict:
    """Call Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8") if params else None
    with urllib.request.urlopen(url, data=data, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_bot_module(bot_path: Path, bot_name: str):
    entrypoint = bot_path / "bot.py"
    if not entrypoint.exists():
        raise RuntimeError(f"bot.py no existe: {entrypoint}")

    module_name = f"factory_api_bot_{bot_name}"
    spec = importlib.util.spec_from_file_location(module_name, entrypoint)
    if not spec or not spec.loader:
        raise RuntimeError(f"No se pudo cargar bot: {entrypoint}")

    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(bot_path))
    try:
        spec.loader.exec_module(module)
    finally:
        if sys.path and sys.path[0] == str(bot_path):
            sys.path.pop(0)

    return module


def get_bot_info(bot_name: str) -> dict:
    registry = read_json(FACTORY_DIR / "bots" / "registry.json")
    bot_info = registry.get(bot_name)
    if not isinstance(bot_info, dict):
        raise HTTPException(status_code=404, detail=f"Bot no registrado: {bot_name}")
    return bot_info


def run_wizard_skill(wizard_complete: dict) -> str:
    from factory.engine import SkillLoader, SkillRunner
    loader = SkillLoader(
        internal_root=FACTORY_DIR / "skills" / "internos",
        external_root=FACTORY_DIR / "skills" / "externos",
    )
    runner = SkillRunner(loader)

    # Paso 1: generar contenido de archivos sin escribir en disco
    agent_context = {
        **wizard_complete["context"],
        "dry_run": False,
        "to_files": True,
        "base_dir": "factory",
    }
    files_result = runner.run(wizard_complete["skill"], agent_context, source="internos")
    if not files_result.get("ok"):
        return f"Error generando agente: {files_result.get('error')}"

    nombre = wizard_complete["context"].get("nombre", "")
    files = files_result["data"]["files"]

    # Paso 2: commitear archivos al repo via github_push
    repo = os.getenv("GITHUB_REPO", "")
    branch = os.getenv("GITHUB_BRANCH", "main")
    push_context = {
        "repo": repo,
        "branch": branch,
        "message": f"feat: add agent {nombre}",
        "files": files,
        "dry_run": False,
    }
    push_result = runner.run("github_push", push_context, source="internos")
    if not push_result.get("ok"):
        return f"Error commiteando agente: {push_result.get('error')}"

    return f"Agente '{nombre}' creado y commiteado en {repo}. Haz git pull para verlo."


def process_bot_update(bot_name: str, update: dict) -> dict:
    bot_info = get_bot_info(bot_name)
    token_env = bot_info.get("token_env", "")
    token = os.getenv(token_env)
    if not token:
        raise HTTPException(status_code=500, detail=f"Variable de entorno faltante: {token_env}")

    chat_id = (update.get("message") or {}).get("chat", {}).get("id")
    state = CONVERSATION_STATE.get(str(chat_id), {})

    bot_path = FACTORY_DIR / bot_info.get("path", f"bots/{bot_name}")
    try:
        bot_module = load_bot_module(bot_path, bot_name)
        handle_update = getattr(bot_module, "handle_update")
        result = handle_update(update, state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    new_state = result.get("state", {}) if isinstance(result, dict) else {}
    CONVERSATION_STATE[str(chat_id)] = new_state

    response = result.get("response") if isinstance(result, dict) else None

    if isinstance(result, dict) and result.get("done"):
        response = run_wizard_skill({"skill": result["skill"], "context": result["context"]})
        CONVERSATION_STATE[str(chat_id)] = {}

    sent = False
    if chat_id and response:
        telegram_request(token, "sendMessage", {"chat_id": chat_id, "text": response})
        sent = True

    return {
        "ok": True,
        "bot": bot_name,
        "sent": sent,
        "command": result.get("command") if isinstance(result, dict) else None,
    }


load_env_file()
app = FastAPI(title="Factory API", version="0.1.0")


@app.get("/")
def root():
    return {"ok": True, "service": "factory_api", "docs": "/docs"}


@app.get("/health")
def health():
    bots = read_json(FACTORY_DIR / "bots" / "registry.json")
    skills = read_json(FACTORY_DIR / "skills" / "registry.json")
    agents = read_json(FACTORY_DIR / "agents" / "registry.json")
    mcps = read_json(FACTORY_DIR / "mcp" / "registry.json")
    return {
        "ok": True,
        "timestamp": datetime.utcnow().isoformat(),
        "bots": len(bots),
        "skills": len(skills),
        "agents": len(agents),
        "mcps": len(mcps),
    }


@app.post("/webhook/{bot_name}")
async def webhook(bot_name: str, request: Request):
    update = await request.json()
    return process_bot_update(bot_name, update)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
