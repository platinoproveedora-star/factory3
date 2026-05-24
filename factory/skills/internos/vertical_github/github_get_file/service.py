"""Service for github_get_file - reads a file from a GitHub repository."""
from __future__ import annotations
import base64
import json
import os
import urllib.request


class GithubGetFileService:

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
        if not context.get("repo"):
            return False, "repo es requerido (owner/repo)"
        if not context.get("path"):
            return False, "path es requerido"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        repo = context["repo"]
        path = context["path"]
        branch = context.get("branch", "")
        url_path = f"/repos/{repo}/contents/{path}"
        if branch:
            url_path += f"?ref={branch}"
        try:
            result = self._request("GET", url_path)
            content = base64.b64decode(result["content"]).decode("utf-8")
            return {"ok": True, "data": {"path": path, "content": content, "sha": result["sha"], "size": result["size"]}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

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
            return json.loads(response.read().decode("utf-8"))
