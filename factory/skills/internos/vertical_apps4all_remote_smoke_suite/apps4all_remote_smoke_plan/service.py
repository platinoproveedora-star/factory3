from __future__ import annotations

from urllib.parse import urlparse


class Apps4AllRemoteSmokePlanService:
    def ejecutar(self, context: dict) -> dict:
        module_code = str(context.get("module_code") or "").strip()
        app_url = str(context.get("app_url") or context.get("url") or "").strip().rstrip("/")
        if not module_code:
            return {"ok": False, "error": "module_code requerido"}
        if not self._valid_url(app_url):
            return {"ok": False, "error": "app_url https requerido"}

        paths = context.get("paths") or ["/", "/login"]
        checks = [{"name": f"GET {path}", "url": f"{app_url}{path if str(path).startswith('/') else '/' + str(path)}", "expected_status": [200, 302, 307, 308]} for path in paths]
        if context.get("sso_token_placeholder", True):
            checks.append({"name": "SSO redirect shape", "url": f"{app_url}/?sso=<token>", "expected_status": [302, 307, 308], "dry_only": True})
        return {"ok": True, "data": {"module_code": module_code, "app_url": app_url, "checks": checks, "dry_run_default": True}}

    def _valid_url(self, value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
