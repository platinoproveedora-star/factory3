from __future__ import annotations

import importlib.util
from pathlib import Path


class Apps4AllFactoryBuildOrchestratorService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        plan = self._run_service(
            repo_root,
            "vertical_apps4all_factory",
            "apps4all_factory_build_plan",
            "Apps4AllFactoryBuildPlanService",
            context,
        )
        if not plan.get("ok"):
            return plan

        data = plan.get("data") or {}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"plan": data, "would_run": data.get("steps") or []}}
        if context.get("confirm_factory_build") is not True:
            return {"ok": False, "error": "confirm_factory_build=true requerido para orquestar writes"}

        # v1 intentionally stays conservative: execute only non-destructive dry-run capable delegates.
        results = []
        for step in data.get("steps") or []:
            if step["name"] in {"auth_bridge", "publish_check", "release"}:
                results.append({"step": step["name"], "result": "pending_delegate_execution"})
            else:
                results.append({"step": step["name"], "result": "manual_or_future_delegate"})
        return {"ok": True, "message": "factory orchestration planned", "data": {"plan": data, "results": results}}

    def _run_service(self, repo_root: Path, vertical: str, skill_dir: str, class_name: str, context: dict) -> dict:
        service_file = repo_root / "factory" / "skills" / "internos" / vertical / skill_dir / "service.py"
        if not service_file.exists():
            return {"ok": False, "error": f"{vertical}/{skill_dir} no encontrado"}
        spec = importlib.util.spec_from_file_location(f"_{vertical}_{skill_dir}_service", service_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": f"no se pudo cargar {vertical}/{skill_dir}"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, class_name)().ejecutar(context)
