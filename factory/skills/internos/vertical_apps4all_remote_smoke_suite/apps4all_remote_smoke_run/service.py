from __future__ import annotations

import importlib.util
import urllib.error
import urllib.request
from pathlib import Path


class Apps4AllRemoteSmokeRunService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        plan = self._plan(repo_root, context)
        if not plan.get("ok"):
            return plan
        checks = (plan.get("data") or {}).get("checks") or []
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"planned_checks": checks}}
        if context.get("confirm_remote_smoke") is not True:
            return {"ok": False, "error": "confirm_remote_smoke=true requerido para requests reales"}

        results = []
        for check in checks:
            if check.get("dry_only"):
                results.append({"name": check["name"], "status": "skipped", "reason": "dry_only"})
                continue
            results.append(self._get(check))
        blockers = [item for item in results if item.get("status") == "fail"]
        return {"ok": not blockers, "data": {"results": results, "summary": {"blockers": len(blockers), "checks": len(results)}}, "error": f"{len(blockers)} smoke blockers" if blockers else None}

    def _plan(self, repo_root: Path, context: dict) -> dict:
        service_file = repo_root / "factory" / "skills" / "internos" / "vertical_apps4all_remote_smoke_suite" / "apps4all_remote_smoke_plan" / "service.py"
        spec = importlib.util.spec_from_file_location("_apps4all_remote_smoke_plan_service", service_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "apps4all remote smoke plan no disponible"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.Apps4AllRemoteSmokePlanService().ejecutar(context)

    def _get(self, check: dict) -> dict:
        req = urllib.request.Request(check["url"], headers={"User-Agent": "FactoryFactory/0.1 (+https://github.com/)"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                code = res.getcode()
        except urllib.error.HTTPError as exc:
            code = exc.code
        except Exception as exc:
            return {"name": check["name"], "url": check["url"], "status": "fail", "error": str(exc)}
        expected = check.get("expected_status") or [200]
        return {"name": check["name"], "url": check["url"], "http_status": code, "status": "pass" if code in expected else "fail"}
