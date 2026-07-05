from __future__ import annotations

import importlib.util
from pathlib import Path


class Apps4AllDeploySyncService:
    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)
        repo_root = Path(__file__).resolve().parents[5]
        plan = self._run_service(
            repo_root,
            "vertical_apps4all_release",
            "apps4all_release_plan",
            "Apps4AllReleasePlanService",
            context,
        )
        if not plan.get("ok"):
            return plan

        if dry_run:
            return {"ok": True, "message": "dry_run", "data": {"plan": plan.get("data"), "would_run": self._would_run(plan.get("data") or {})}}

        if context.get("confirm_release") is not True:
            return {"ok": False, "error": "confirm_release=true requerido para deploy real"}

        data = plan.get("data") or {}
        vercel_project = data["vercel_project"]
        envs = context.get("envs") or {}
        repo = data.get("repo") or context.get("repo") or ""
        root_dir = data["project_path"]

        results = {}
        results["project_create"] = self._run_service(
            repo_root,
            "vertical_vercel",
            "vercel_project_create",
            "VercelProjectCreateService",
            {"name": vercel_project, "repo": repo, "framework": "nextjs", "root_dir": root_dir, "dry_run": False},
        )
        if not results["project_create"].get("ok"):
            return {"ok": False, "error": "vercel_project_create fallo", "data": results}

        project_id = (results["project_create"].get("data") or {}).get("project_id") or vercel_project
        results["env_sync"] = self._run_service(
            repo_root,
            "vertical_vercel",
            "vercel_env_sync",
            "VercelEnvSyncService",
            {"project_id": project_id, "envs": envs, "target": context.get("target", ["production", "preview"]), "dry_run": False},
        )
        if not results["env_sync"].get("ok"):
            return {"ok": False, "error": "vercel_env_sync fallo", "data": results}

        results["deploy_trigger"] = self._run_service(
            repo_root,
            "vertical_vercel",
            "vercel_deploy_trigger",
            "VercelDeployTriggerService",
            {"project_id": project_id, "target": context.get("deploy_target", "production"), "dry_run": False},
        )
        if not results["deploy_trigger"].get("ok"):
            return {"ok": False, "error": "vercel_deploy_trigger fallo", "data": results}

        app_url = (results["deploy_trigger"].get("data") or {}).get("url") or self._default_app_url(context, vercel_project)
        if context.get("activate_url", True):
            results["module_url_activate"] = self._run_service(
                repo_root,
                "vertical_apps4all_release",
                "apps4all_module_url_activate",
                "Apps4AllModuleUrlActivateService",
                {
                    **context,
                    "module_code": data["module_code"],
                    "app_url": app_url,
                    "status": context.get("marketplace_status", "live"),
                    "dry_run": False,
                },
            )
            if not results["module_url_activate"].get("ok"):
                return {"ok": False, "error": "apps4all_module_url_activate fallo", "data": results}

        return {"ok": True, "message": "release synced", "data": {"app_url": app_url, "project_id": project_id, "results": results}}

    def _would_run(self, plan: dict) -> list[dict]:
        skills = plan.get("skills") or {}
        return [
            skills.get("publish_check"),
            skills.get("vercel_project_create"),
            skills.get("vercel_env_sync"),
            skills.get("vercel_deploy_trigger"),
            skills.get("module_url_activate"),
        ]

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

    def _default_app_url(self, context: dict, vercel_project: str) -> str:
        explicit_url = str(context.get("app_url") or "").strip().rstrip("/")
        if explicit_url:
            return explicit_url
        scheme = str(context.get("url_scheme") or "https").strip()
        suffix = str(context.get("vercel_domain_suffix") or "vercel.app").strip().lstrip(".")
        return f"{scheme}://{vercel_project}.{suffix}"
