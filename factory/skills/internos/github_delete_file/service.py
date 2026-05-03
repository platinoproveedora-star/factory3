"""Service for github_delete_file - deletes a file from a GitHub repository."""
from __future__ import annotations
import json
import os
import urllib.request


class GithubDeleteFileService:

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
            return False, "repo es requerido"
        if not context.get("path"):
            return False, "path es requerido"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        repo = context["repo"]
        path = context["path"]
        branch = context.get("branch", "main")
        message = context.get("message", f"chore: delete {path}")
        sha = context.get("sha")
        if not sha:
            try:
                file_info = self._request("GET", f"/repos/{repo}/contents/{path}?ref={branch}")
                sha = file_info["sha"]
            except Exception as exc:
                return {"ok": False, "error": f"No se pudo obtener SHA: {exc}"}
        try:
            self._request("DELETE", f"/repos/{repo}/contents/{path}", payload={"message": message, "sha": sha, "branch": branch})
            return {"ok": True, "message": f"Archivo '{path}' eliminado de {repo}", "data": {"path": path, "repo": repo}}
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
