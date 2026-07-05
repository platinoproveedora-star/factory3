from __future__ import annotations

import json
import re
from pathlib import Path


MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class Apps4AllAuthBridgePlanService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        project_path = self._resolve_project_path(repo_root, context)
        project_json = self._read_json(project_path / "project.json") if project_path else {}

        module_code = str(context.get("module_code") or project_json.get("module_code") or "").strip()
        if not MODULE_RE.match(module_code):
            return {"ok": False, "error": "module_code requerido con formato snake_case"}

        cookie_name = str(context.get("cookie_name") or f"{module_code}_token").strip()
        apps4all_cookie = str(context.get("apps4all_cookie_name") or "apps4all_token").strip()
        plan = {
            "module_code": module_code,
            "cookie_name": cookie_name,
            "apps4all_cookie_name": apps4all_cookie,
            "project_path": self._rel(project_path, repo_root) if project_path else None,
            "required_files": [
                "lib/auth.ts",
                "lib/platform.ts",
                "middleware.ts",
                "app/login/page.tsx",
                "app/api/auth/login/route.ts",
                "app/api/auth/logout/route.ts",
                "app/api/auth/me/route.ts",
            ],
            "required_env": [
                "PLATFORM_JWT_SECRET",
                "PLATFORM_SUPABASE_URL",
                "PLATFORM_SUPABASE_SERVICE_ROLE_KEY",
            ],
            "contract": {
                "sso_query_param": "sso",
                "local_cookie": cookie_name,
                "apps4all_cookie": apps4all_cookie,
                "grant_module_code": module_code,
                "grant_statuses": ["active", "trialing", "manual", "comped"],
            },
        }
        return {"ok": True, "data": plan}

    def _resolve_project_path(self, repo_root: Path, context: dict) -> Path | None:
        raw = str(context.get("project_path") or "").strip()
        if not raw:
            return None
        path = Path(raw)
        if not path.is_absolute():
            path = repo_root / path
        return path if path.exists() else None

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def _rel(self, path: Path | None, repo_root: Path) -> str | None:
        if path is None:
            return None
        try:
            return str(path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            return str(path)
