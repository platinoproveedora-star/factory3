from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,60}$")


class Apps4AllReleasePlanService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        project_result = self._resolve_project(repo_root, context)
        if not project_result.get("ok"):
            return project_result

        project_path = project_result["path"]
        project_json = self._read_json(project_path / "project.json")
        if project_json is None:
            return {"ok": False, "error": "project.json requerido"}

        module_code = str(context.get("module_code") or project_json.get("module_code") or "").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or project_json.get("company_id") or "").strip()
        project_code = str(context.get("project_code") or project_json.get("project_code") or "").strip()
        schema = str(context.get("schema") or project_json.get("schema") or "").strip()
        vercel_project = str(context.get("vercel_project") or self._default_vercel_project(company_id, module_code)).strip()
        if not PROJECT_RE.match(vercel_project):
            return {"ok": False, "error": "vercel_project invalido"}

        root_dir = self._rel(project_path, repo_root)
        required_env = list(dict.fromkeys(project_json.get("requires_env") or []))
        provided_envs = context.get("envs") or {}
        missing_env_values = [key for key in required_env if key not in provided_envs]
        repo = str(context.get("repo") or context.get("github_repo") or "").strip()
        default_app_url = self._default_app_url(context, vercel_project)

        plan = {
            "company_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
            "schema": schema,
            "project_path": root_dir,
            "vercel_project": vercel_project,
            "repo": repo,
            "required_env": required_env,
            "missing_env_values": missing_env_values,
            "skills": {
                "publish_check": {
                    "skill": "vertical_factory_productization/factory_module_publish_check",
                    "context": {"project_path": root_dir, "module_code": module_code},
                },
                "vercel_project_create": {
                    "skill": "vertical_vercel/vercel_project_create",
                    "context": {"name": vercel_project, "repo": repo, "framework": "nextjs", "root_dir": root_dir, "dry_run": True},
                },
                "vercel_env_sync": {
                    "skill": "vertical_vercel/vercel_env_sync",
                    "context": {"project_id": vercel_project, "envs": provided_envs, "target": ["production", "preview"], "dry_run": True},
                },
                "vercel_deploy_trigger": {
                    "skill": "vertical_vercel/vercel_deploy_trigger",
                    "context": {"project_id": vercel_project, "target": "production", "dry_run": True},
                },
                "module_url_activate": {
                    "skill": "vertical_apps4all_release/apps4all_module_url_activate",
                    "context": {"module_code": module_code, "app_url": default_app_url, "dry_run": True},
                },
            },
            "steps": [
                "correr publish_check",
                "crear o validar proyecto Vercel",
                "sincronizar env vars",
                "disparar deploy production",
                "validar estado READY",
                "guardar URL en Marketplace",
                "actualizar Apps4All env/config si se usa NEXT_PUBLIC_<MODULO>_URL",
            ],
        }
        return {"ok": True, "data": plan}

    def _resolve_project(self, repo_root: Path, context: dict) -> dict:
        raw = str(context.get("project_path") or "").strip()
        if raw:
            path = Path(raw)
            if not path.is_absolute():
                path = repo_root / path
            if not path.exists():
                return {"ok": False, "error": "project_path no existe"}
            return {"ok": True, "path": path}

        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("project_code") or "").strip()
        if not company_id or not project_code:
            return {"ok": False, "error": "project_path o company_id/project_code requerido"}
        base = repo_root / "companies" / company_id / "projects"
        matches = sorted(path for path in base.glob(f"{project_code}*") if path.is_dir())
        if not matches:
            return {"ok": False, "error": "proyecto no encontrado"}
        return {"ok": True, "path": matches[0]}

    def _default_vercel_project(self, company_id: str, module_code: str) -> str:
        raw = f"{company_id}-{module_code}".lower().replace("_", "-")
        return re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")[:60]

    def _default_app_url(self, context: dict, vercel_project: str) -> str:
        explicit_url = str(context.get("app_url") or "").strip().rstrip("/")
        if explicit_url:
            return explicit_url
        scheme = str(context.get("url_scheme") or "https").strip()
        suffix = str(context.get("vercel_domain_suffix") or "vercel.app").strip().lstrip(".")
        return f"{scheme}://{vercel_project}.{suffix}"

    def _read_json(self, path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None

    def _rel(self, path: Path, repo_root: Path) -> str:
        try:
            return str(path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            return str(path)
