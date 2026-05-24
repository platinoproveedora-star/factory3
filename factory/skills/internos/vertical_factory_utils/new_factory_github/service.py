"""Creates a GitHub repo and uploads all files from a local factory."""
from __future__ import annotations
import base64
import json
import os
import urllib.request
from pathlib import Path

IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORE_FILES = {".env"}


class NewFactoryGithubService:

    def ejecutar(self, context: dict) -> dict:
        ok, error = self._validar(context)
        if not ok:
            return {"ok": False, "error": error}
        if context.get("dry_run"):
            files = self._collect_files(Path(context["factory_dir"]))
            return {"ok": True, "message": "dry_run", "data": {"files": len(files)}}

        factory_dir = Path(context["factory_dir"]).resolve()
        files = self._collect_files(factory_dir)

        if context.get("create_repo", True):
            repo = self._create_repo(context)
        else:
            repo = context["repo"]

        uploaded = self._upload_files(repo, context.get("branch", "main"), files)

        return {
            "ok": True,
            "message": f"Repo '{repo}' listo con {uploaded} archivos",
            "data": {
                "repo": repo,
                "repo_url": f"https://github.com/{repo}",
                "files_uploaded": uploaded,
            },
        }

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        factory_dir = context.get("factory_dir")
        if not factory_dir:
            return False, "factory_dir es requerido"
        root = Path(factory_dir)
        if not root.exists():
            return False, f"factory_dir no existe: {factory_dir}"
        for required in ("factory_api.py", "requirements.txt", "factory/skills/registry.json"):
            if not (root / required).exists():
                return False, f"falta {required}"
        if context.get("create_repo", True) and not context.get("repo_name"):
            return False, "repo_name es requerido"
        if not context.get("create_repo", True) and not context.get("repo"):
            return False, "repo es requerido cuando create_repo es false"
        return True, None

    def _collect_files(self, root: Path) -> list[tuple[Path, str]]:
        files = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if set(rel.parts) & IGNORE_DIRS:
                continue
            if path.name in IGNORE_FILES or path.suffix == ".pyc":
                continue
            files.append((path, rel.as_posix()))
        return files

    def _create_repo(self, context: dict) -> str:
        org = context.get("github_org", "")
        payload = {
            "name": context["repo_name"],
            "description": context.get("description", "Generated factory"),
            "private": context.get("private", True),
            "auto_init": True,
        }
        path = f"/orgs/{org}/repos" if org else "/user/repos"
        result = self._gh("POST", path, payload)
        return result["full_name"]

    def _upload_files(self, repo: str, branch: str, files: list[tuple[Path, str]]) -> int:
        count = 0
        for source, relative in files:
            content_b64 = base64.b64encode(source.read_bytes()).decode()
            sha = self._get_sha(repo, relative, branch)
            payload: dict = {"message": f"factory: {relative}", "content": content_b64, "branch": branch}
            if sha:
                payload["sha"] = sha
            try:
                self._gh("PUT", f"/repos/{repo}/contents/{relative}", payload)
                count += 1
            except Exception:
                pass
        return count

    def _get_sha(self, repo: str, path: str, branch: str) -> str | None:
        try:
            return self._gh("GET", f"/repos/{repo}/contents/{path}?ref={branch}").get("sha")
        except Exception:
            return None

    def _gh(self, method: str, path: str, payload: dict | None = None) -> dict:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN no configurada")
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"https://api.github.com{path}", data=data, method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}
