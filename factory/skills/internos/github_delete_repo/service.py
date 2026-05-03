"""Service for github_delete_repo - deletes a GitHub repository."""
from __future__ import annotations
import json
import os
import urllib.request


class GithubDeleteRepoService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run: no se elimino nada", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        if not context.get("repo"):
            return False, "repo es requerido (owner/repo)"
        if context.get("confirm") is not True:
            return False, "confirm: true es requerido para eliminar un repo"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        repo = context["repo"]
        try:
            self._request("DELETE", f"/repos/{repo}")
            return {"ok": True, "message": f"Repo '{repo}' eliminado", "data": {"repo": repo}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, method: str, path: str, payload: dict | None = None):
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
