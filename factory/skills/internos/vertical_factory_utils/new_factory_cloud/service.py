"""Service for new_factory_cloud - deploys a generated factory to cloud."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from pathlib import Path


IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORE_FILES = {".env"}
FORBIDDEN_TERMS = ["Factory", "FACTORY", "factory", "factory"]
RENDER_TERMINAL = {"live", "deactivated", "build_failed", "update_failed", "canceled"}


class NewFactoryCloudService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        factory_dir = Path(context["factory_dir"]).resolve()
        files = self._collect_files(factory_dir)
        legacy_hits = self._legacy_hits(factory_dir)
        if legacy_hits:
            return {"ok": False, "error": "factory_dir contiene nombres legacy", "data": {"hits": legacy_hits[:20]}}

        plan = self._plan(context, factory_dir, files)
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": plan}

        steps: list[dict] = []
        repo = context.get("repo", "")
        try:
            if context.get("create_repo", True):
                repo = self._github_create_repo(context)
                self._step(steps, "create_github_repo", True, {"repo": repo})
            else:
                self._step(steps, "use_existing_repo", True, {"repo": repo})

            uploaded = self._github_upload_files(repo, context.get("branch", "main"), files)
            self._step(steps, "upload_factory_files", True, {"files_uploaded": uploaded})

            service = self._render_create_service(context, repo)
            service_id = service.get("id", "")
            service_url = service.get("url", "")
            self._step(steps, "create_render_service", True, {"service_id": service_id, "url": service_url})

            if context.get("wait_for_deploy", True) and service_id:
                service_url, deploy_status = self._render_wait(service_id, int(context.get("max_wait_seconds", 360)))
                self._step(steps, "wait_for_deploy", True, {"url": service_url, "status": deploy_status})

            webhook_url = self._webhook_url(service_url, context)
            if webhook_url and context.get("bot_token"):
                self._telegram_set_webhook(context["bot_token"], webhook_url)
                self._step(steps, "set_telegram_webhook", True, {"webhook_url": webhook_url})

            return {
                "ok": True,
                "message": "factory cloud deploy listo",
                "data": {
                    "repo": repo,
                    "repo_url": f"https://github.com/{repo}",
                    "service_id": service_id,
                    "service_url": service_url,
                    "webhook_url": webhook_url,
                    "steps": steps,
                },
            }
        except Exception as exc:  # noqa: BLE001
            self._step(steps, "failed", False, error=str(exc))
            return {"ok": False, "error": str(exc), "data": {"steps": steps, "repo": repo}}

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        factory_dir = context.get("factory_dir")
        if not factory_dir:
            return False, "factory_dir es requerido"
        root = Path(factory_dir)
        if not root.exists() or not root.is_dir():
            return False, f"factory_dir no existe: {factory_dir}"
        for required in ("factory_api.py", "requirements.txt", "factory/skills/registry.json"):
            if not (root / required).exists():
                return False, f"falta {required}"
        if context.get("create_repo", True):
            if not context.get("repo_name"):
                return False, "repo_name es requerido cuando create_repo es true"
        elif not context.get("repo"):
            return False, "repo es requerido cuando create_repo es false"
        if not context.get("service_name"):
            return False, "service_name es requerido"
        if not context.get("render_owner_id"):
            return False, "render_owner_id es requerido"
        return True, None

    def _plan(self, context: dict, factory_dir: Path, files: list[tuple[Path, str]]) -> dict:
        repo = context.get("repo") or self._target_repo_name(context)
        service_name = context["service_name"]
        bot_name = context.get("bot_name", "factory_admin")
        return {
            "factory_dir": str(factory_dir),
            "create_repo": context.get("create_repo", True),
            "repo": repo,
            "branch": context.get("branch", "main"),
            "service_name": service_name,
            "render_owner_id": context["render_owner_id"],
            "bot_name": bot_name,
            "files_to_upload": len(files),
            "sample_files": [relative for _, relative in files[:20]],
            "start_command": "uvicorn factory_api:app --host 0.0.0.0 --port $PORT",
            "webhook_path": f"/webhook/{bot_name}",
        }

    def _collect_files(self, root: Path) -> list[tuple[Path, str]]:
        files: list[tuple[Path, str]] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(root)
            parts = set(relative_path.parts)
            if parts & IGNORE_DIRS:
                continue
            if path.name in IGNORE_FILES or path.suffix == ".pyc":
                continue
            files.append((path, relative_path.as_posix()))
        return files

    def _legacy_hits(self, root: Path) -> list[str]:
        hits: list[str] = []
        for path, relative in self._collect_files(root):
            if path.suffix.lower() not in {".py", ".json", ".md", ".txt", ".yml", ".yaml", ".example"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for term in FORBIDDEN_TERMS:
                if term in text:
                    hits.append(f"{relative}: {term}")
                    break
        return hits

    def _target_repo_name(self, context: dict) -> str:
        org = context.get("github_org", "")
        repo_name = context.get("repo_name", "")
        return f"{org}/{repo_name}" if org else repo_name

    def _github_create_repo(self, context: dict) -> str:
        org = context.get("github_org", "")
        payload = {
            "name": context["repo_name"],
            "description": context.get("description", "Generated factory"),
            "private": context.get("private", True),
            "auto_init": True,
        }
        path = f"/orgs/{org}/repos" if org else "/user/repos"
        result = self._github("POST", path, payload)
        return result["full_name"]

    def _github_upload_files(self, repo: str, branch: str, files: list[tuple[Path, str]]) -> int:
        count = 0
        for source, relative in files:
            content_b64 = base64.b64encode(source.read_bytes()).decode("utf-8")
            sha = self._github_get_sha(repo, relative, branch)
            payload: dict = {
                "message": f"factory: upload {relative}",
                "content": content_b64,
                "branch": branch,
            }
            if sha:
                payload["sha"] = sha
            self._github("PUT", f"/repos/{repo}/contents/{relative}", payload)
            count += 1
        return count

    def _github_get_sha(self, repo: str, path: str, branch: str) -> str | None:
        try:
            result = self._github("GET", f"/repos/{repo}/contents/{path}?ref={branch}")
            return result.get("sha")
        except Exception:
            return None

    def _github(self, method: str, path: str, payload: dict | None = None) -> dict:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN no configurada")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            f"https://api.github.com{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    def _render_create_service(self, context: dict, repo: str) -> dict:
        env_vars = {"TELEGRAM_TOKEN": context.get("bot_token", ""), **context.get("env_vars", {})}
        payload = {
            "type": "web_service",
            "name": context["service_name"],
            "ownerId": context["render_owner_id"],
            "repo": f"https://github.com/{repo}",
            "autoDeploy": "yes",
            "branch": context.get("branch", "main"),
            "envVars": [{"key": key, "value": value} for key, value in env_vars.items() if value],
            "serviceDetails": {
                "env": "python",
                "plan": context.get("plan", "free"),
                "region": context.get("region", "oregon"),
                "numInstances": 1,
                "envSpecificDetails": {
                    "buildCommand": context.get("build_command", "pip install -r requirements.txt"),
                    "startCommand": context.get("start_command", "uvicorn factory_api:app --host 0.0.0.0 --port $PORT"),
                },
            },
        }
        result = self._render("POST", "/services", payload)
        service = result.get("service", result)
        return {
            "id": service.get("id", ""),
            "name": service.get("name", ""),
            "url": service.get("serviceDetails", {}).get("url", ""),
        }

    def _render_wait(self, service_id: str, max_wait: int) -> tuple[str, str]:
        elapsed = 0
        interval = 20
        while True:
            deploys = self._render("GET", f"/services/{service_id}/deploys?limit=1")
            if deploys:
                deploy = deploys[0].get("deploy", deploys[0])
                status = deploy.get("status", "")
                if status in RENDER_TERMINAL:
                    if status != "live":
                        raise RuntimeError(f"Deploy termino con estado: {status}")
                    service = self._render("GET", f"/services/{service_id}")
                    url = service.get("serviceDetails", {}).get("url", "")
                    return url, status
            if elapsed >= max_wait:
                raise TimeoutError(f"Deploy no termino en {max_wait}s")
            time.sleep(interval)
            elapsed += interval

    def _render(self, method: str, path: str, payload: dict | None = None):
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    def _webhook_url(self, service_url: str, context: dict) -> str:
        if not service_url:
            return ""
        bot_name = context.get("bot_name", "factory_admin")
        return f"{service_url.rstrip('/')}/webhook/{bot_name}"

    def _telegram_set_webhook(self, token: str, webhook_url: str) -> None:
        payload = json.dumps({"url": webhook_url}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/setWebhook",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError(result.get("description", "setWebhook fallo"))

    def _step(self, steps: list[dict], name: str, ok: bool, data=None, error=None) -> None:
        steps.append({"step": name, "ok": ok, "data": data, "error": error})
