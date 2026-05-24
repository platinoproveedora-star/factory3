"""Service for github_push - commits files to GitHub repo via API."""

from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import PurePosixPath


GITHUB_API = "https://api.github.com"


class GithubPushService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        repo = context["repo"]
        branch = context.get("branch", "main")
        message = context.get("message", "chore: add files via Factory")
        files = context["files"]

        if context.get("dry_run", False):
            return {
                "ok": True,
                "message": "dry_run: no se escribio nada",
                "data": {"repo": repo, "branch": branch, "files": [f["path"] for f in files]},
            }

        token = os.getenv(context.get("token_env", "GITHUB_TOKEN"))
        if not token:
            return {"ok": False, "error": "GITHUB_TOKEN no encontrado en variables de entorno"}

        results = []
        for file in files:
            result = self._push_file(token, repo, branch, file["path"], file["content"], message)
            results.append({"path": file["path"], **result})
            if not result["ok"]:
                return {"ok": False, "error": f"fallo en {file['path']}: {result.get('error')}", "data": results}

        return {
            "ok": True,
            "message": f"{len(files)} archivo(s) commiteados en {repo}@{branch}",
            "data": {"repo": repo, "branch": branch, "commits": results},
        }

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        if not context.get("repo"):
            return False, "repo es requerido (ej: owner/repo)"
        if not context.get("files"):
            return False, "files es requerido — lista de {path, content}"
        if not isinstance(context["files"], list):
            return False, "files debe ser una lista"
        for f in context["files"]:
            if not isinstance(f, dict) or "path" not in f or "content" not in f:
                return False, "cada file debe tener 'path' y 'content'"
        return True, None

    def _push_file(self, token: str, repo: str, branch: str, path: str, content: str, message: str) -> dict:
        clean_path = str(PurePosixPath(path))
        url = f"{GITHUB_API}/repos/{repo}/contents/{clean_path}"
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        sha = self._get_sha(token, url, branch)

        payload: dict = {"message": message, "content": encoded, "branch": branch}
        if sha:
            payload["sha"] = sha

        try:
            result = self._request("PUT", url, token, payload)
            return {"ok": True, "sha": result.get("content", {}).get("sha", "")}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _get_sha(self, token: str, url: str, branch: str) -> str | None:
        try:
            result = self._request("GET", f"{url}?ref={branch}", token)
            return result.get("sha")
        except Exception:
            return None

    def _request(self, method: str, url: str, token: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
