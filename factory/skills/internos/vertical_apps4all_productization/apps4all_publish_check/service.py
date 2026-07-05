from __future__ import annotations

import importlib.util
from pathlib import Path


class Apps4AllPublishCheckService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        service_file = repo_root / "factory" / "skills" / "internos" / "vertical_factory_productization" / "factory_module_publish_check" / "service.py"
        spec = importlib.util.spec_from_file_location("_apps4all_legacy_publish_check_service", service_file)
        if spec is None or spec.loader is None:
            return {"ok": False, "error": "apps4all publish check base no disponible"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.FactoryModulePublishCheckService().ejecutar(context)
        if result.get("ok"):
            result["message"] = "apps4all publish check ready"
        return result
