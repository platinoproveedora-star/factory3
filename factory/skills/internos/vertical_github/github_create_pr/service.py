"""Service for github_create_pr - creates a pull request in a GitHub repository."""
from __future__ import annotations
import json
import os
import urllib.request


class GithubCreatePrService:

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
        for field in ("repo", "title", "head", "base"):
            if not context.get(field):
                return False, f"{field} es requerido"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        repo = context["repo"]
        payload = {
            "title": context["title"],
            "head": context["head"],
            "base": context["base"],
            "body": context.get("body", ""),
            "draft": context.get("draft", False),
        }
        try:
            result = self._request("POST", f"/repos/{repo}/pulls", payload=payload)
            return {"ok": True, "data": {"number": result["number"], "html_url": result["html_url"], "state": result["state"]}}
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
