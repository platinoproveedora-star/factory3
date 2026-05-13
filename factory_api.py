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

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request


BASE_DIR = Path(__file__).parent
FACTORY_DIR = BASE_DIR / "factory"


def load_env_file(path: Path = BASE_DIR / ".env") -> None:
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
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


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


# --- State persistence via Supabase ---

def _load_state(chat_id: str) -> dict:
    try:
        from factory.engine import SupabaseClient
        db = SupabaseClient({})
        r = db.rest_select("bot_states", filters={"chat_id": chat_id}, select="state", limit=1)
        if r.get("ok"):
            rows = r.get("data") or []
            if rows:
                return rows[0].get("state") or {}
    except Exception:
        pass
    return {}


def _save_state(chat_id: str, state: dict) -> None:
    try:
        from factory.engine import SupabaseClient
        db = SupabaseClient({})
        existing = db.rest_select("bot_states", filters={"chat_id": chat_id}, select="id", limit=1)
        if existing.get("ok") and (existing.get("data") or []):
            db.rest_update("bot_states", values={"state": state, "updated_at": datetime.utcnow().isoformat()}, filters={"chat_id": chat_id})
        else:
            db.rest_insert("bot_states", {"chat_id": chat_id, "state": state})
    except Exception:
        pass


# --- Background skill runner ---

def _run_background_skill(bg_task: dict, token: str, chat_id: int) -> None:
    try:
        from factory.engine import SkillLoader, SkillRunner
        ext = FACTORY_DIR / "skills" / "externos"
        ext.mkdir(parents=True, exist_ok=True)
        loader = SkillLoader(internal_root=FACTORY_DIR / "skills" / "internos", external_root=ext, extra_roots={"meta": FACTORY_DIR / "skills" / "meta", "eval": FACTORY_DIR / "skills" / "eval"})
        runner = SkillRunner(loader)
        result = runner.run(bg_task["skill"], bg_task["context"], source="internos")
        response = bg_task.get("on_done", "Listo.")
        if result.get("ok") and result.get("data", {}).get("response"):
            response = result["data"]["response"]
        elif not result.get("ok"):
            response = f"Error: {result.get('error', 'desconocido')}"
        telegram_request(token, "sendMessage", {"chat_id": chat_id, "text": response, "parse_mode": "HTML"})
    except Exception as e:
        telegram_request(token, "sendMessage", {"chat_id": chat_id, "text": f"Error en background: {e}"})


# --- Wizard skill runner ---

def run_wizard_skill(wizard_complete: dict) -> str:
    from factory.engine import SkillLoader, SkillRunner
    ext = FACTORY_DIR / "skills" / "externos"
    ext.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(internal_root=FACTORY_DIR / "skills" / "internos", external_root=ext)
    runner = SkillRunner(loader)
    agent_context = {**wizard_complete["context"], "dry_run": False, "to_files": True, "base_dir": "factory"}
    files_result = runner.run(wizard_complete["skill"], agent_context, source="internos")
    if not files_result.get("ok"):
        return f"Error generando agente: {files_result.get('error')}"
    nombre = wizard_complete["context"].get("nombre", "")
    files = files_result["data"]["files"]
    repo = os.getenv("GITHUB_REPO", "")
    branch = os.getenv("GITHUB_BRANCH", "main")
    push_result = runner.run("github_push", {"repo": repo, "branch": branch, "message": f"feat: add agent {nombre}", "files": files, "dry_run": False}, source="internos")
    if not push_result.get("ok"):
        return f"Error commiteando agente: {push_result.get('error')}"
    return f"Agente '{nombre}' creado y commiteado en {repo}."


# --- Main bot update processor ---

def process_bot_update(bot_name: str, update: dict, background_tasks: BackgroundTasks | None = None) -> dict:
    bot_info = get_bot_info(bot_name)
    token_env = bot_info.get("token_env", "")
    token = os.getenv(token_env)
    if not token:
        raise HTTPException(status_code=500, detail=f"Variable de entorno faltante: {token_env}")

    # Handle callback_query (button clicks)
    is_callback = "callback_query" in update
    if is_callback:
        cq = update["callback_query"]
        chat_id = cq.get("message", {}).get("chat", {}).get("id")
        cq_id = cq.get("id")
        text = cq.get("data", "")
        # Answer callback to stop loading spinner
        telegram_request(token, "answerCallbackQuery", {"callback_query_id": cq_id})
        # Rebuild update as message for uniform handling
        update = {
            "message": {
                "chat": {"id": chat_id},
                "from": cq.get("from", {}),
                "text": text,
            }
        }

    message = (update.get("message") or {})
    chat_id = message.get("chat", {}).get("id")

    # Load persistent state
    state = _load_state(str(chat_id)) if chat_id else {}

    bot_path = FACTORY_DIR / bot_info.get("path", f"bots/{bot_name}")
    try:
        bot_module = load_bot_module(bot_path, bot_name)
        handle_update = getattr(bot_module, "handle_update")
        result = handle_update(update, state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    new_state = result.get("state", {}) if isinstance(result, dict) else {}

    # Persist state
    if chat_id:
        _save_state(str(chat_id), new_state)

    response = result.get("response") if isinstance(result, dict) else None
    reply_markup = result.get("reply_markup") if isinstance(result, dict) else None

    # Handle wizard done
    if isinstance(result, dict) and result.get("done"):
        response = run_wizard_skill({"skill": result["skill"], "context": result["context"]})

    # Handle background tasks (long operations like seed)
    if isinstance(result, dict) and result.get("background_task") and background_tasks and chat_id:
        bg = result["background_task"]
        if background_tasks:
            background_tasks.add_task(_run_background_skill, bg, token, chat_id)

    sent = False
    if chat_id and response:
        params: dict = {"chat_id": chat_id, "text": response, "parse_mode": "HTML"}
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        telegram_request(token, "sendMessage", params)
        sent = True

    return {
        "ok": True,
        "bot": bot_name,
        "sent": sent,
        "command": result.get("command") if isinstance(result, dict) else None,
    }


load_env_file()
app = FastAPI(title="Factory API", version="0.1.0")

_data_runner = None

def _get_data_runner():
    global _data_runner
    if _data_runner is None:
        from factory.engine import SkillLoader, SkillRunner
        ext = FACTORY_DIR / "skills" / "externos"
        ext.mkdir(parents=True, exist_ok=True)
        loader = SkillLoader(internal_root=FACTORY_DIR / "skills" / "internos", external_root=ext, extra_roots={"meta": FACTORY_DIR / "skills" / "meta", "eval": FACTORY_DIR / "skills" / "eval"})
        _data_runner = SkillRunner(loader)
    return _data_runner


@app.get("/")
def root():
    return {"ok": True, "service": "factory_api", "docs": "/docs"}


@app.get("/health")
def health():
    bots   = read_json(FACTORY_DIR / "bots" / "registry.json")
    skills = read_json(FACTORY_DIR / "skills" / "registry.json")
    agents = read_json(FACTORY_DIR / "agents" / "registry.json")
    return {
        "ok": True,
        "timestamp": datetime.utcnow().isoformat(),
        "bots":   len(bots),
        "skills": len(skills),
        "agents": len(agents),
    }


@app.get("/data/{skill_name}")
def data(skill_name: str, request: Request):
    params = dict(request.query_params)
    try:
        result = _get_data_runner().run(skill_name, params, source="internos")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "error"))
    return result.get("data", {})


@app.post("/cron/tasks")
def cron_tasks(request: Request):
    """Render Cron endpoint — ejecuta meta_task_runner cada 5 min."""
    from factory.engine import SkillLoader, SkillRunner
    skills_dir = FACTORY_DIR / "skills"
    ext = skills_dir / "externos"
    ext.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(internal_root=skills_dir / "internos", external_root=ext)
    runner = SkillRunner(loader)
    meta_source = str(skills_dir / "meta")
    batch_size  = int(os.getenv("CRON_TASK_BATCH", "20"))
    result = runner.run("meta_task_runner", {"batch_size": batch_size, "dry_run": False}, source=meta_source)
    return {"ok": result.get("ok"), "message": result.get("message"), "data": result.get("data")}


@app.post("/run/{skill_name:path}")
async def run_skill(skill_name: str, request: Request):
    secret = os.getenv("FACTORY_RUN_SECRET", "")
    if secret:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {secret}":
            raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    try:
        result = _get_data_runner().run(skill_name, body, source="internos")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result


@app.post("/webhook/{bot_name}")
async def webhook(bot_name: str, request: Request, background_tasks: BackgroundTasks):
    update = await request.json()
    return process_bot_update(bot_name, update, background_tasks)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
