from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


class GithubRepoDeliveryCheckService:
    def ejecutar(self, context: dict) -> dict:
        repo = context.get("repo", "")
        if not repo:
            return {"ok": False, "error": "repo requerido owner/name"}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": {"repo": repo}}
        try:
            info = self._request("GET", f"/repos/{repo}")
            branch = context.get("branch") or info.get("default_branch", "main")
            tree = self._request("GET", f"/repos/{repo}/git/trees/{branch}?recursive=1").get("tree", [])
            findings = self._findings(tree)
            return {"ok": True, "data": {
                "repo": repo,
                "branch": branch,
                "ready_for_transfer": not any(f["severity"] == "blocker" for f in findings),
                "findings": findings,
                "checks": {
                    "has_readme": any(item.get("path", "").lower() == "readme.md" for item in tree),
                    "files_checked": len(tree),
                },
            }}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _findings(self, tree: list[dict]) -> list[dict]:
        findings = []
        risky_names = {".env", ".env.local", ".env.production", "secrets.json", "credentials.json", "service-account.json"}
        risky_patterns = [r"token", r"secret", r"password", r"apikey", r"private[_-]?key"]
        for item in tree:
            path = item.get("path", "")
            name = path.rsplit("/", 1)[-1].lower()
            low = path.lower()
            if name in risky_names:
                findings.append({"severity": "blocker", "path": path, "issue": "archivo sensible no debe entregarse en repo"})
            elif any(re.search(p, low) for p in risky_patterns):
                findings.append({"severity": "warning", "path": path, "issue": "nombre sugiere secreto o credencial; revisar antes de transferir"})
        if not any(item.get("path", "").lower() == "readme.md" for item in tree):
            findings.append({"severity": "warning", "path": "README.md", "issue": "falta README de entrega"})
        return findings

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
