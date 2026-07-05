from __future__ import annotations


class Apps4AllOpsMonitoringPlanService:
    def ejecutar(self, context: dict) -> dict:
        module_code = str(context.get("module_code") or "").strip()
        project_path = str(context.get("project_path") or "").strip()
        if not module_code:
            return {"ok": False, "error": "module_code requerido"}
        checks = [
            {"name": "publish_check", "skill": "vertical_apps4all_productization/apps4all_publish_check", "context": {"project_path": project_path, "module_code": module_code}},
            {"name": "auth_bridge", "skill": "vertical_apps4all_auth_bridge/apps4all_auth_bridge_health_check", "context": {"project_path": project_path, "module_code": module_code}},
            {"name": "release_plan", "skill": "vertical_apps4all_release/apps4all_release_plan", "context": {"project_path": project_path, "module_code": module_code}},
            {"name": "remote_smoke", "skill": "vertical_apps4all_remote_smoke_suite/apps4all_remote_smoke_plan", "context": {"module_code": module_code, "app_url": context.get("app_url") or "<app_url>"}},
            {"name": "billing_plan", "skill": "vertical_apps4all_billing_stripe/apps4all_billing_plan", "context": {"module_code": module_code}},
        ]
        return {"ok": True, "data": {"module_code": module_code, "project_path": project_path, "checks": checks}}
