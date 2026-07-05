from __future__ import annotations

import json
from pathlib import Path


class Apps4AllAuthBridgeHealthCheckService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        raw = str(context.get("project_path") or "").strip()
        if not raw:
            return {"ok": False, "error": "project_path requerido"}
        project_path = Path(raw)
        if not project_path.is_absolute():
            project_path = repo_root / project_path
        if not project_path.exists():
            return {"ok": False, "error": "project_path no existe"}

        project_json = self._read_json(project_path / "project.json")
        module_code = str(context.get("module_code") or project_json.get("module_code") or "").strip()
        checks = []
        for rel in [
            "project.json",
            "lib/auth.ts",
            "lib/platform.ts",
            "middleware.ts",
            "app/login/page.tsx",
            "app/api/auth/login/route.ts",
            "app/api/auth/logout/route.ts",
        ]:
            checks.append(self._check(f"file:{rel}", (project_path / rel).exists(), f"{rel} existe"))

        auth_text = self._read_text(project_path / "lib/auth.ts")
        middleware_text = self._read_text(project_path / "middleware.ts")
        checks.append(self._check("apps4all_cookie", "apps4all_token" in auth_text + middleware_text, "acepta cookie Apps4All"))
        checks.append(self._check("sso_query", 'get("sso")' in middleware_text or "get('sso')" in middleware_text, "acepta query sso"))
        checks.append(self._check("jwt_secret", "PLATFORM_JWT_SECRET" in auth_text + middleware_text, "usa PLATFORM_JWT_SECRET"))
        checks.append(self._check("platform_grants", "access_grants" in self._read_text(project_path / "lib/platform.ts"), "lee grants plataforma"))
        if module_code:
            checks.append(self._check("module_code", module_code in auth_text + middleware_text + self._read_text(project_path / "project.json"), "module_code presente en config/codigo"))

        blockers = [item for item in checks if item["status"] == "fail"]
        return {
            "ok": not blockers,
            "data": {
                "ready": not blockers,
                "module_code": module_code,
                "summary": {"blockers": len(blockers), "checks": len(checks)},
                "checks": checks,
            },
            "error": f"{len(blockers)} blockers auth bridge" if blockers else None,
        }

    def _check(self, name: str, passed: bool, message: str) -> dict:
        return {"name": name, "status": "pass" if passed else "fail", "message": message}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            return ""
