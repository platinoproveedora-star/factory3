"""Orchestrator: runs all new_factory sub-skills in sequence."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path


def _load(skill_name: str, class_name: str):
    skill_dir = Path(__file__).resolve().parent.parent / skill_name
    spec = importlib.util.spec_from_file_location(f"{skill_name}_svc", skill_dir / "service.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(skill_dir))
    try:
        spec.loader.exec_module(mod)
    finally:
        if sys.path and sys.path[0] == str(skill_dir):
            sys.path.pop(0)
    return getattr(mod, class_name)()


class NewFactoryCloudV2Service:

    def ejecutar(self, context: dict) -> dict:
        ok, error = self._validar(context)
        if not ok:
            return {"ok": False, "error": error}
        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": self._safe_plan(context)}

        steps: list[dict] = []

        # 1. GitHub
        github_ctx = {
            "factory_dir": context["factory_dir"],
            "repo_name": context["repo_name"],
            "github_org": context.get("github_org", ""),
            "branch": context.get("branch", "main"),
            "private": context.get("private", True),
            "create_repo": context.get("create_repo", True),
        }
        if not context.get("create_repo", True):
            github_ctx["repo"] = context["repo"]

        gh_result = _load("new_factory_github", "NewFactoryGithubService").ejecutar(github_ctx)
        steps.append({"step": "github", **gh_result})
        if not gh_result.get("ok"):
            return {"ok": False, "error": gh_result.get("error"), "data": {"steps": steps}}
        repo = gh_result["data"]["repo"]

        # 2. Render
        render_ctx = {
            "repo": repo,
            "service_name": context.get("service_name", context["repo_name"]),
            "render_owner_id": context["render_owner_id"],
            "branch": context.get("branch", "main"),
            "env_vars": context.get("env_vars", {}),
            "plan": context.get("plan", "free"),
            "region": context.get("region", "oregon"),
            "wait_for_deploy": context.get("wait_for_deploy", True),
            "max_wait_seconds": context.get("max_wait_seconds", 360),
        }
        render_result = _load("new_factory_render", "NewFactoryRenderService").ejecutar(render_ctx)
        steps.append({"step": "render", **render_result})
        if not render_result.get("ok"):
            return {"ok": False, "error": render_result.get("error"), "data": {"steps": steps, "repo": repo}}
        service_url = render_result["data"]["service_url"]
        service_id = render_result["data"]["service_id"]

        # 3. Telegram
        tg_ctx = {
            "bot_token": context["bot_token"],
            "service_url": service_url,
            "bot_name": context.get("bot_name", "factory_admin"),
            "repo": repo,
            "branch": context.get("branch", "main"),
        }
        tg_result = _load("new_factory_telegram", "NewFactoryTelegramService").ejecutar(tg_ctx)
        steps.append({"step": "telegram", **tg_result})
        if not tg_result.get("ok"):
            return {"ok": False, "error": tg_result.get("error"), "data": {"steps": steps, "repo": repo, "service_url": service_url}}
        webhook_url = tg_result["data"]["webhook_url"]

        # 4. Supabase (opcional)
        if context.get("supabase_url") and context.get("supabase_access_token") and context.get("supabase_project_ref"):
            sb_ctx = {
                "supabase_url": context["supabase_url"],
                "supabase_access_token": context["supabase_access_token"],
                "supabase_project_ref": context["supabase_project_ref"],
                "tables": context.get("supabase_tables", ["sessions", "agent_memory"]),
            }
            sb_result = _load("new_factory_supabase", "NewFactorySupabaseService").ejecutar(sb_ctx)
            steps.append({"step": "supabase", **sb_result})

        return {
            "ok": True,
            "message": f"Fabrica '{context['repo_name']}' desplegada y lista",
            "data": {
                "repo": repo,
                "repo_url": f"https://github.com/{repo}",
                "service_id": service_id,
                "service_url": service_url,
                "webhook_url": webhook_url,
                "bot_username": tg_result["data"].get("bot_username"),
                "steps": steps,
            },
        }

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        for field in ("factory_dir", "repo_name", "render_owner_id", "bot_token"):
            if not context.get(field):
                return False, f"{field} es requerido"
        return True, None

    def _safe_plan(self, context: dict) -> dict:
        env_vars = context.get("env_vars", {})
        return {
            "factory_dir": context.get("factory_dir"),
            "repo_name": context.get("repo_name"),
            "repo": context.get("repo", ""),
            "create_repo": context.get("create_repo", True),
            "private": context.get("private", True),
            "branch": context.get("branch", "main"),
            "service_name": context.get("service_name", context.get("repo_name")),
            "render_owner_id_set": bool(context.get("render_owner_id")),
            "bot_token_set": bool(context.get("bot_token")),
            "bot_name": context.get("bot_name", "factory_admin"),
            "supabase_enabled": all([
                context.get("supabase_url"),
                context.get("supabase_access_token"),
                context.get("supabase_project_ref"),
            ]),
            "env_vars": {key: bool(value) for key, value in env_vars.items()},
            "steps": ["github", "render", "telegram", "supabase_optional"],
        }
