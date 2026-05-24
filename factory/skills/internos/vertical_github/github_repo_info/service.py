"""Service for github_repo_info - gets metadata of a GitHub repository."""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request


class GithubRepoInfoService:

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
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        repo = context["repo"]
        try:
            result = self._request("GET", f"/repos/{repo}")
            return {"ok": True, "data": {
                "full_name": result["full_name"],
                "exists": True,
                "private": result["private"],
                "default_branch": result["default_branch"],
                "description": result.get("description", ""),
                "html_url": result["html_url"],
                "clone_url": result["clone_url"],
                "size": result["size"],
            }}
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {"ok": True, "data": {"repo": repo, "exists": False}}
            return {"ok": False, "error": str(exc)}
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
