"""Service for github_list_branches - lists branches in a GitHub repository."""
from __future__ import annotations
import json
import os
import urllib.request


class GithubListBranchesService:

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
        per_page = min(context.get("per_page", 30), 100)
        protected = context.get("protected_only", False)
        path = f"/repos/{repo}/branches?per_page={per_page}"
        if protected:
            path += "&protected=true"
        try:
            result = self._request("GET", path)
            branches = [
                {
                    "name": b["name"],
                    "sha": b["commit"]["sha"],
                    "protected": b.get("protected", False),
                }
                for b in result
            ]
            return {"ok": True, "data": {"branches": branches, "count": len(branches)}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _request(self, method: str, path: str) -> list:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN no configurada")
        req = urllib.request.Request(
            f"https://api.github.com{path}", method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
