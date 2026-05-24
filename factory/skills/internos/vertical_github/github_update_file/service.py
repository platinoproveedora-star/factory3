"""Service for github_update_file - updates an existing file in a GitHub repo."""
from __future__ import annotations
import base64
import json
import os
import urllib.request


class GithubUpdateFileService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        for field in ("repo", "path", "content"):
            if not context.get(field) and context.get(field) != "":
                return False, f"{field} es requerido"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        repo = context["repo"]
        path = context["path"].lstrip("/")
        content = context["content"]
        message = context.get("message", f"Update {path}")
        branch = context.get("branch", "")
        try:
            sha = context.get("sha") or self._get_sha(repo, path, branch)
            if not sha:
                return {"ok": False, "error": f"Archivo '{path}' no existe. Usa github_push para crearlo."}
            content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            payload: dict = {"message": message, "content": content_b64, "sha": sha}
            if branch:
                payload["branch"] = branch
            result = self._request("PUT", f"/repos/{repo}/contents/{path}", payload=payload)
            commit = result.get("commit", {})
            return {
                "ok": True,
                "data": {
                    "path": path,
                    "sha": result.get("content", {}).get("sha", ""),
                    "commit_sha": commit.get("sha", ""),
                    "message": message,
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _get_sha(self, repo: str, path: str, branch: str) -> str | None:
        try:
            url = f"/repos/{repo}/contents/{path}"
            if branch:
                url += f"?ref={branch}"
            result = self._request("GET", url)
            return result.get("sha")
        except Exception:
            return None

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN no configurada")
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(
            f"https://api.github.com{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
