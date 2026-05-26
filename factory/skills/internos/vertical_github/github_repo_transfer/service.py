from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class GithubRepoTransferService:
    def ejecutar(self, context: dict) -> dict:
        repo = context.get("repo", "")
        if not repo and context.get("owner") and context.get("repo_name"):
            repo = f"{context.get('owner')}/{context.get('repo_name')}"
        if not repo and context.get("owner") and context.get("name"):
            repo = f"{context.get('owner')}/{context.get('name')}"
        new_owner = context.get("new_owner", "")
        if not repo:
            return {"ok": False, "error": "repo requerido owner/name"}
        if not new_owner:
            return {"ok": False, "error": "new_owner requerido"}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": {"repo": repo, "new_owner": new_owner}}
        if not context.get("confirm", False):
            return {"ok": False, "error": "confirm:true requerido para transferir repos"}
        payload = {"new_owner": new_owner}
        if context.get("new_name"):
            payload["new_name"] = context["new_name"]
        if context.get("team_ids"):
            payload["team_ids"] = context["team_ids"]
        try:
            result = self._request("POST", f"/repos/{repo}/transfer", payload)
            return {"ok": True, "data": {"repo": repo, "new_owner": new_owner, "result": result}}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": f"HTTP {exc.code}: {exc.read().decode(errors='replace')}"}
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
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
