from __future__ import annotations

import importlib.util
from pathlib import Path


class Apps4AllModuleClonePlanService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        service_file = repo_root / "factory" / "skills" / "internos" / "vertical_factory_productization" / "factory_module_clone_plan" / "service.py"
        spec = importlib.util.spec_from_file_location("_apps4all_module_clone_plan_base_service", service_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "apps4all module clone base no disponible"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.FactoryModuleClonePlanService().ejecutar(context)
        if result.get("ok"):
            result["message"] = "apps4all clone plan ready"
        return result
