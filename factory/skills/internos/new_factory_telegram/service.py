"""Sets Telegram webhook and registers the admin bot in the factory repo."""
from __future__ import annotations
import base64
import json
import os
import urllib.request


BOT_PY = '''\
"""Admin bot for factory."""
from __future__ import annotations

COMMANDS = {
    "/start": "Hola! Soy el bot admin de esta fabrica. Escribe /ayuda para ver los comandos.",
    "/ayuda": "Comandos disponibles:\\n/start - Iniciar\\n/ayuda - Ayuda\\n/estado - Estado de la fabrica",
    "/estado": "Fabrica activa y funcionando.",
}

def handle_update(update: dict, state: dict) -> dict:
    message = update.get("message", {})
    text = (message.get("text") or "").strip()
    response = COMMANDS.get(text, "Comando no reconocido. Escribe /ayuda para ver los comandos disponibles.")
    return {
        "response": response,
        "state": {},
        "command": text.lstrip("/") if text.startswith("/") else None,
    }
'''


class NewFactoryTelegramService:

    def ejecutar(self, context: dict) -> dict:
        ok, error = self._validar(context)
        if not ok:
            return {"ok": False, "error": error}

        bot_token = context["bot_token"]
        service_url = context["service_url"].rstrip("/")
        bot_name = context.get("bot_name", "factory_admin")
        webhook_url = f"{service_url}/webhook/{bot_name}"
        repo = context["repo"]
        branch = context.get("branch", "main")

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"webhook_url": webhook_url}}

        steps: list[dict] = []

        # 1. Validar bot token
        try:
            bot_info = self._tg("getMe", bot_token).get("result", {})
            steps.append({"step": "validate_token", "ok": True, "username": bot_info.get("username")})
        except Exception as exc:
            return {"ok": False, "error": f"Token invalido: {exc}", "data": {"steps": steps}}

        # 2. Subir archivos del bot al repo
        try:
            pushed = self._push_bot_files(repo, branch, bot_name)
            steps.append({"step": "push_bot_files", "ok": True, "files": pushed})
        except Exception as exc:
            steps.append({"step": "push_bot_files", "ok": False, "error": str(exc)})
            return {"ok": False, "error": f"Error subiendo archivos del bot: {exc}", "data": {"steps": steps}}

        # 3. Setear webhook
        try:
            self._set_webhook(bot_token, webhook_url)
            steps.append({"step": "set_webhook", "ok": True, "url": webhook_url})
        except Exception as exc:
            steps.append({"step": "set_webhook", "ok": False, "error": str(exc)})
            return {"ok": False, "error": f"Error seteando webhook: {exc}", "data": {"steps": steps}}

        # 4. Verificar webhook
        try:
            wh = self._tg("getWebhookInfo", bot_token).get("result", {})
            configured = bool(wh.get("url"))
            steps.append({"step": "verify_webhook", "ok": configured, "url": wh.get("url", "")})
        except Exception as exc:
            steps.append({"step": "verify_webhook", "ok": False, "error": str(exc)})

        return {
            "ok": True,
            "message": f"Bot '{bot_name}' configurado",
            "data": {
                "bot_username": bot_info.get("username"),
                "webhook_url": webhook_url,
                "steps": steps,
            },
        }

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        for field in ("bot_token", "service_url", "repo"):
            if not context.get(field):
                return False, f"{field} es requerido"
        return True, None

    def _push_bot_files(self, repo: str, branch: str, bot_name: str) -> list[str]:
        registry = {
            bot_name: {
                "nombre": bot_name,
                "bot_type": "admin",
                "path": f"bots/{bot_name}",
                "entrypoint": "bot.py",
                "token_env": "TELEGRAM_TOKEN",
                "commands": ["start", "ayuda", "estado"],
                "version": "0.1.0",
            }
        }
        config = {
            "bot_name": bot_name,
            "bot_type": "admin",
            "token_env": "TELEGRAM_TOKEN",
            "commands": ["start", "ayuda", "estado"],
        }

        files = {
            f"factory/bots/registry.json": json.dumps(registry, indent=2, ensure_ascii=False),
            f"factory/bots/{bot_name}/config.json": json.dumps(config, indent=2, ensure_ascii=False),
            f"factory/bots/{bot_name}/bot.py": BOT_PY,
        }

        pushed = []
        for path, content in files.items():
            content_b64 = base64.b64encode(content.encode()).decode()
            sha = self._get_sha(repo, path, branch)
            payload: dict = {"message": f"factory: add {path}", "content": content_b64, "branch": branch}
            if sha:
                payload["sha"] = sha
            self._gh("PUT", f"/repos/{repo}/contents/{path}", payload)
            pushed.append(path)
        return pushed

    def _get_sha(self, repo: str, path: str, branch: str) -> str | None:
        try:
            return self._gh("GET", f"/repos/{repo}/contents/{path}?ref={branch}").get("sha")
        except Exception:
            return None

    def _tg(self, method: str, token: str) -> dict:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/{method}", method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    def _set_webhook(self, token: str, url: str) -> None:
        data = json.dumps({"url": url}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/setWebhook",
            data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read().decode())
        if not result.get("ok"):
            raise ValueError(result.get("description", "setWebhook fallo"))

    def _gh(self, method: str, path: str, payload: dict | None = None) -> dict:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN no configurada")
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"https://api.github.com{path}", data=data, method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}
