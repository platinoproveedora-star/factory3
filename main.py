#!/usr/bin/env python3
"""Factory CLI — control local de la fabrica."""

import importlib.util
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import click

from factory.engine import SkillLoader, SkillRunner

BASE_DIR    = Path(__file__).parent
FACTORY_DIR = BASE_DIR / "factory"


# =============================================================================
# HELPERS
# =============================================================================

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


def leer_registry(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace").strip() or "{}")
    except json.JSONDecodeError:
        return {}


def parse_context(context_json: str, context_file: str | None) -> dict:
    if context_file:
        p = Path(context_file)
        if not p.exists():
            raise click.ClickException(f"context-file no existe: {context_file}")
        raw = p.read_text(encoding="utf-8", errors="replace")
    else:
        raw = context_json
    try:
        ctx = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"JSON invalido: {exc}") from exc
    if not isinstance(ctx, dict):
        raise click.ClickException("context debe ser un objeto JSON")
    return ctx


def run_skill(nombre: str, context: dict, source: str = "internos") -> dict:
    loader = SkillLoader(
        FACTORY_DIR / "skills" / "internos",
        FACTORY_DIR / "skills" / "externos",
    )
    return SkillRunner(loader).run(nombre, context, source=source)


def telegram_request(token: str, method: str, params: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8") if params else None
    with urllib.request.urlopen(url, data=data, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def load_bot_module(bot_path: Path, bot_name: str):
    entrypoint = bot_path / "bot.py"
    if not entrypoint.exists():
        raise click.ClickException(f"bot.py no existe: {entrypoint}")
    spec = importlib.util.spec_from_file_location(f"factory_bot_{bot_name}", entrypoint)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(bot_path))
    try:
        spec.loader.exec_module(module)
    finally:
        if sys.path and sys.path[0] == str(bot_path):
            sys.path.pop(0)
    return module


# =============================================================================
# CLI
# =============================================================================

@click.group()
def cli():
    """Factory CLI — control local de la fabrica."""
    load_env_file()


# =============================================================================
# list
# =============================================================================

@cli.command("list")
@click.option("--tipo", default="all",
              type=click.Choice(["skills", "agents", "bots", "all"]))
def list_cmd(tipo):
    """Lista todo lo registrado en la fabrica."""
    if tipo in ("skills", "all"):
        click.echo("\nSkills:")
        reg = leer_registry(FACTORY_DIR / "skills" / "registry.json")
        if reg:
            by_vertical: dict = {}
            for nombre, info in reg.items():
                v = info.get("vertical", "?")
                by_vertical.setdefault(v, []).append(nombre)
            for vertical, nombres in sorted(by_vertical.items()):
                click.echo(f"  [{vertical}]")
                for n in sorted(nombres):
                    click.echo(f"    {n}")
        else:
            click.echo("  (ninguno)")

    if tipo in ("agents", "all"):
        click.echo("\nAgentes:")
        reg = leer_registry(FACTORY_DIR / "agents" / "registry.json")
        if reg:
            for nombre, info in reg.items():
                click.echo(f"  {nombre} - {info.get('descripcion', '')}")
        else:
            click.echo("  (ninguno)")

    if tipo in ("bots", "all"):
        click.echo("\nBots:")
        reg = leer_registry(FACTORY_DIR / "bots" / "registry.json")
        if reg:
            for nombre, info in reg.items():
                click.echo(f"  {nombre} (token_env: {info.get('token_env', '?')})")
        else:
            click.echo("  (ninguno)")


# =============================================================================
# run-skill
# =============================================================================

@cli.command("run-skill")
@click.argument("nombre")
@click.option("--context", "context_json", default="{}", help="Contexto JSON inline")
@click.option("--context-file", default=None, help="Archivo JSON con contexto")
@click.option("--source", default="internos", type=click.Choice(["internos", "externos"]))
def run_skill_cmd(nombre, context_json, context_file, source):
    """Ejecuta un skill de la fabrica.

    \b
    Ejemplo:
      python main.py run-skill ig_caption_generator --context-file ctx.json
    """
    ctx = parse_context(context_json, context_file)
    result = run_skill(nombre, ctx, source)
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


# =============================================================================
# run-bot
# =============================================================================

def _tg_send(token: str, chat_id: int | str, text: str, reply_markup: dict | None = None) -> None:
    params: dict = {
        "chat_id":    str(chat_id),
        "text":       text[:4096],
        "parse_mode": "HTML",
    }
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    try:
        telegram_request(token, "sendMessage", params)
    except Exception as exc:
        click.echo(f"   [WARN] sendMessage: {exc}")


def _tg_answer_callback(token: str, callback_query_id: str) -> None:
    try:
        telegram_request(token, "answerCallbackQuery", {"callback_query_id": callback_query_id})
    except Exception:
        pass


def _extract_chat_and_text(update: dict) -> tuple[int | None, str, str]:
    """Returns (chat_id, text, callback_query_id)."""
    if "callback_query" in update:
        cq      = update["callback_query"]
        chat_id = (cq.get("message") or {}).get("chat", {}).get("id")
        text    = (cq.get("data") or "").strip()
        return chat_id, text, cq.get("id", "")
    msg     = update.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    text    = (msg.get("text") or "").strip()
    return chat_id, text, ""


def _run_background_task(task: dict) -> None:
    import threading
    skill_name = task.get("skill", "")
    ctx        = task.get("context", {})
    if not skill_name:
        return
    def _run():
        try:
            loader = SkillLoader(
                FACTORY_DIR / "skills" / "internos",
                FACTORY_DIR / "skills" / "externos",
            )
            SkillRunner(loader).run(skill_name, ctx, source="internos")
        except Exception as exc:
            click.echo(f"   [WARN] background_task {skill_name}: {exc}")
    threading.Thread(target=_run, daemon=True).start()


@cli.command("run-bot")
@click.argument("bot_name")
@click.option("--interval", default=2, type=int, help="Segundos entre polling")
@click.option("--once", is_flag=True, help="Procesa updates pendientes una vez y sale")
def run_bot_cmd(bot_name, interval, once):
    """Corre un bot en modo polling local (sin webhook)."""
    reg = leer_registry(FACTORY_DIR / "bots" / "registry.json")
    bot_info = reg.get(bot_name)
    if not bot_info:
        raise click.ClickException(f"Bot no registrado: {bot_name}")

    token = os.getenv(bot_info.get("token_env", ""))
    if not token:
        raise click.ClickException(f"Env var faltante: {bot_info.get('token_env')}")

    bot_path = FACTORY_DIR / bot_info.get("path", f"bots/{bot_name}")
    bot_module = load_bot_module(bot_path, bot_name)
    handle_update = getattr(bot_module, "handle_update")

    telegram_request(token, "deleteWebhook")
    me = telegram_request(token, "getMe")
    username = (me.get("result") or {}).get("username", "")
    click.echo(f"[OK] Polling activo: {bot_name} @{username}  (Ctrl+C para detener)")

    # Per-chat state persisted in memory for the session
    chat_states: dict[int, dict] = {}

    offset = None
    while True:
        try:
            params: dict = {"timeout": 20, "allowed_updates": '["message","callback_query"]'}
            if offset is not None:
                params["offset"] = offset
            updates = telegram_request(token, "getUpdates", params)
            for update in updates.get("result", []):
                offset = update["update_id"] + 1

                chat_id, text, cq_id = _extract_chat_and_text(update)
                if not chat_id:
                    continue

                # Rebuild update with normalised text so handle_update always sees message
                if cq_id:
                    _tg_answer_callback(token, cq_id)
                    update = {
                        **update,
                        "message": {
                            **(update.get("callback_query", {}).get("message") or {}),
                            "text": text,
                            "from": (update.get("callback_query") or {}).get("from"),
                            "chat": {"id": chat_id},
                        },
                    }

                state  = chat_states.get(chat_id, {})
                result = handle_update(update, state)

                if not isinstance(result, dict):
                    continue

                # Unwrap ok/data envelope if present
                data = result.get("data", result) if result.get("ok") is not None else result

                response     = data.get("response")
                new_state    = data.get("state")
                reply_markup = data.get("reply_markup")
                bg_task      = data.get("background_task")

                if new_state is not None:
                    chat_states[chat_id] = new_state

                if response:
                    _tg_send(token, chat_id, response, reply_markup)
                    click.echo(f"   [{chat_id}] update {update['update_id']}: {response[:60]!r}")

                if bg_task:
                    _run_background_task(bg_task)

            if once:
                break
            time.sleep(max(interval, 1))
        except KeyboardInterrupt:
            click.echo("\n[OK] Polling detenido")
            break
        except Exception as exc:
            click.echo(f"[WARN] {exc}")
            if once:
                break
            time.sleep(max(interval, 1))


# =============================================================================
# set-webhook
# =============================================================================

@cli.command("set-webhook")
@click.argument("bot_name")
@click.option("--url", "base_url", required=True, help="URL publica base del servicio")
@click.option("--dry-run", is_flag=True)
def set_webhook_cmd(bot_name, base_url, dry_run):
    """Registra el webhook Telegram de un bot."""
    reg = leer_registry(FACTORY_DIR / "bots" / "registry.json")
    bot_info = reg.get(bot_name)
    if not bot_info:
        raise click.ClickException(f"Bot no registrado: {bot_name}")

    token = os.getenv(bot_info.get("token_env", ""))
    if not token:
        raise click.ClickException(f"Env var faltante: {bot_info.get('token_env')}")

    webhook_url = f"{base_url.rstrip('/')}/webhook/{bot_name}"
    click.echo(f"   Webhook URL: {webhook_url}")

    if dry_run:
        click.echo("[OK] Dry run — no se llamo a Telegram")
        return

    result = telegram_request(token, "setWebhook", {"url": webhook_url, "drop_pending_updates": "true"})
    if result.get("ok"):
        click.echo(f"[OK] Webhook registrado para {bot_name}")
    else:
        raise click.ClickException(result.get("description", "Telegram rechazo el webhook"))


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    cli()
