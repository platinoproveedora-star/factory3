"""Service for github_copy_folder - copies a folder from one repo to another."""
from __future__ import annotations
import base64
import json
import os
import urllib.request


class GithubCopyFolderService:

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
        for field in ("src_repo", "src_path", "dst_repo", "dst_path"):
            if not context.get(field):
                return False, f"{field} es requerido"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        src_repo = context["src_repo"]
        src_path = context["src_path"].strip("/")
        dst_repo = context["dst_repo"]
        dst_path = context["dst_path"].strip("/")
        commit_message = context.get("message", f"Copy {src_path} from {src_repo}")
        copied = []
        errors = []
        try:
            files = self._list_all_files(src_repo, src_path)
            for file_info in files:
                src_file_path = file_info["path"]
                rel_path = src_file_path[len(src_path):].lstrip("/")
                dst_file_path = f"{dst_path}/{rel_path}" if rel_path else dst_path
                try:
                    content_b64 = self._get_file_content_b64(src_repo, src_file_path)
                    sha = self._get_existing_sha(dst_repo, dst_file_path)
                    payload = {"message": commit_message, "content": content_b64}
                    if sha:
                        payload["sha"] = sha
                    self._request("PUT", f"/repos/{dst_repo}/contents/{dst_file_path}", payload=payload)
                    copied.append(dst_file_path)
                except Exception as exc:
                    errors.append({"path": src_file_path, "error": str(exc)})
            return {"ok": True, "data": {"copied": copied, "count": len(copied), "errors": errors}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _list_all_files(self, repo: str, path: str) -> list[dict]:
        items = self._request("GET", f"/repos/{repo}/contents/{path}")
        if not isinstance(items, list):
            return [items] if items.get("type") == "file" else []
        files = []
        for item in items:
            if item["type"] == "file":
                files.append(item)
            elif item["type"] == "dir":
                files.extend(self._list_all_files(repo, item["path"]))
        return files

    def _get_file_content_b64(self, repo: str, path: str) -> str:
        result = self._request("GET", f"/repos/{repo}/contents/{path}")
        raw_b64 = result["content"].replace("\n", "")
        decoded = base64.b64decode(raw_b64)
        return base64.b64encode(decoded).decode("utf-8")

    def _get_existing_sha(self, repo: str, path: str) -> str | None:
        try:
            result = self._request("GET", f"/repos/{repo}/contents/{path}")
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
