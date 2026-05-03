"""Service for new_factory - creates a complete factory in local or cloud mode."""
from __future__ import annotations
import base64
import json
import os
import shutil
import time
import urllib.request
from pathlib import Path


TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".env", ".example"}

VERTICAL_ENV_VARS = {
    "factory":          ["ANTHROPIC_API_KEY"],
    "factory_telegram": ["TELEGRAM_TOKEN", "ADMIN_BOT_TOKEN", "ADMIN_CHAT_ID"],
    "factory_supabase": ["SUPABASE_URL", "SUPABASE_PROJECT_REF", "SUPABASE_ACCESS_TOKEN",
                         "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY"],
    "factory_github":   ["GITHUB_TOKEN"],
    "factory_render":   ["RENDER_API_KEY", "RENDER_OWNER_ID"],
    "factory_skills":   [],
    "marketing_ai":     ["ANTHROPIC_API_KEY"],
    "utils":            [],
    "security":         [],
}

RENDER_TERMINAL = {"live", "deactivated", "build_failed", "update_failed", "canceled"}


class NewFactoryService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        mode = context.get("mode", "local")
        if mode == "cloud":
            return self._ejecutar_cloud(context)
        return self._ejecutar_local(context)

    # ------------------------------------------------------------------ #
    # Validacion                                                           #
    # ------------------------------------------------------------------ #

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        if not context.get("factory_name"):
            return False, "factory_name es requerido"
        mode = context.get("mode", "local")
        if mode not in ("local", "cloud"):
            return False, "mode debe ser 'local' o 'cloud'"
        if mode == "cloud":
            for field in ("bot_token", "template_repo", "owner_id"):
                if not context.get(field):
                    return False, f"{field} es requerido para modo cloud"
        return True, None

    # ------------------------------------------------------------------ #
    # MODO LOCAL                                                           #
    # ------------------------------------------------------------------ #

    def _ejecutar_local(self, context: dict) -> dict:
        factory_name = context["factory_name"]
        output_dir = Path(context.get("output_dir", "..")).resolve()
        verticals = context.get("verticals", [])
        source_package_dir = context.get("source_package_dir", "factory")
        package_dir = context.get("package_dir", "factory")
        api_module = context.get("api_module", "factory_api:app")

        source_root = Path(__file__).resolve().parents[4]
        target_root = output_dir / factory_name
        api_file = api_module.split(":", 1)[0] + ".py"

        if target_root.exists():
            return {"ok": False, "error": f"El directorio '{target_root}' ya existe"}

        try:
            for d in [
                f"{package_dir}/skills/internos",
                f"{package_dir}/agents",
                f"{package_dir}/bots",
                f"{package_dir}/mcp",
            ]:
                (target_root / d).mkdir(parents=True, exist_ok=True)

            registry_path = source_root / source_package_dir / "skills/registry.json"
            with open(registry_path, encoding="utf-8") as f:
                full_registry = json.load(f)

            filtered = {k: v for k, v in full_registry.items()
                        if not verticals or v.get("vertical") in verticals}
            filtered = self._rewrite_data(filtered, source_package_dir, package_dir)

            self._copy_tree_rewritten(
                source_root / source_package_dir / "engine",
                target_root / package_dir / "engine",
                source_package_dir,
                package_dir,
            )

            self._copy_optional_file_rewritten(
                source_root / "factory_api.py",
                target_root / api_file,
                source_package_dir,
                package_dir,
            )

            self._copy_optional_file_rewritten(
                source_root / "requirements.txt",
                target_root / "requirements.txt",
                source_package_dir,
                package_dir,
            )

            copied_skills = []
            for skill_name, info in filtered.items():
                src = source_root / source_package_dir / info["path"]
                dst = target_root / package_dir / info["path"]
                if src.exists():
                    self._copy_tree_rewritten(src, dst, source_package_dir, package_dir)
                    copied_skills.append(skill_name)

            with open(target_root / package_dir / "skills/registry.json", "w", encoding="utf-8") as f:
                json.dump(filtered, f, indent=2, ensure_ascii=False)

            agents_src = source_root / source_package_dir / "agents/registry.json"
            if agents_src.exists():
                self._copy_optional_file_rewritten(
                    agents_src,
                    target_root / package_dir / "agents/registry.json",
                    source_package_dir,
                    package_dir,
                )

            mcp_src = source_root / source_package_dir / "mcp/registry.json"
            if mcp_src.exists():
                self._copy_optional_file_rewritten(
                    mcp_src,
                    target_root / package_dir / "mcp/registry.json",
                    source_package_dir,
                    package_dir,
                )

            with open(target_root / ".env.example", "w", encoding="utf-8") as f:
                f.write(self._env_example(
                    verticals or list({v.get("vertical", "") for v in filtered.values()}),
                    context,
                ))
            self._write_readme(target_root, factory_name, package_dir, api_module)

            return {
                "ok": True,
                "message": f"Fabrica '{factory_name}' creada en {target_root}",
                "data": {
                    "path": str(target_root),
                    "mode": "local",
                    "package_dir": package_dir,
                    "api_module": api_module,
                    "skills_copied": len(copied_skills),
                    "skills": copied_skills,
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------ #
    # MODO CLOUD                                                           #
    # ------------------------------------------------------------------ #

    def _ejecutar_cloud(self, context: dict) -> dict:
        factory_name   = context["factory_name"]
        bot_token      = context["bot_token"]
        template_repo  = context["template_repo"]
        owner_id       = context["owner_id"]
        verticals      = context.get("verticals", [])
        env_vars       = context.get("env_vars", {})
        branch         = context.get("branch", "main")
        github_org     = context.get("github_org", "")
        webhook_path   = context.get("webhook_path", "/webhook")
        package_dir    = context.get("package_dir", "factory")
        api_module     = context.get("api_module", "factory_api:app")
        max_wait       = int(context.get("max_wait_seconds", 360))

        steps: list[dict] = []

        def step(name: str, ok: bool, data=None, error=None):
            steps.append({"step": name, "ok": ok, "data": data, "error": error})
            return ok

        # 1. Validar bot token
        try:
            bot_info = self._tg_get("getMe", bot_token).get("result", {})
            step("validate_bot_token", True, {"username": bot_info.get("username"), "id": bot_info.get("id")})
        except Exception as exc:
            step("validate_bot_token", False, error=str(exc))
            return {"ok": False, "error": f"Token invalido: {exc}", "steps": steps}

        # 2. Crear repo GitHub
        try:
            repo_full_name = self._gh_create_repo(factory_name, github_org)
            step("create_github_repo", True, {"repo": repo_full_name})
        except Exception as exc:
            step("create_github_repo", False, error=str(exc))
            return {"ok": False, "error": f"Error creando repo: {exc}", "steps": steps}

        # 3. Copiar template al nuevo repo
        try:
            files_copied = self._gh_copy_all(template_repo, repo_full_name, branch)
            step("copy_template", True, {"files_copied": files_copied})
        except Exception as exc:
            step("copy_template", False, error=str(exc))
            return {"ok": False, "error": f"Error copiando template: {exc}", "steps": steps}

        # 4. Filtrar registry por verticals (si se especificaron)
        if verticals:
            try:
                self._gh_filter_registry(repo_full_name, branch, verticals, package_dir)
                step("filter_registry", True, {"verticals": verticals})
            except Exception as exc:
                step("filter_registry", False, error=str(exc))

        # 5. Crear servicio Render
        all_env_vars = {"TELEGRAM_TOKEN": bot_token, **env_vars}
        try:
            service = self._render_create(factory_name, f"https://github.com/{repo_full_name}",
                                          owner_id, branch, all_env_vars, api_module)
            service_id = service["id"]
            step("create_render_service", True, {"service_id": service_id})
        except Exception as exc:
            step("create_render_service", False, error=str(exc))
            return {"ok": False, "error": f"Error creando servicio Render: {exc}", "steps": steps}

        # 6. Esperar deploy
        try:
            service_url, deploy_status = self._render_wait(service_id, max_wait)
            step("wait_for_deploy", True, {"url": service_url, "status": deploy_status})
        except Exception as exc:
            step("wait_for_deploy", False, error=str(exc))
            return {"ok": False, "error": f"Deploy fallo: {exc}", "steps": steps}

        # 7. Configurar webhook Telegram
        webhook_url = f"{service_url.rstrip('/')}{webhook_path}"
        try:
            self._tg_set_webhook(bot_token, webhook_url)
            step("set_webhook", True, {"webhook_url": webhook_url})
        except Exception as exc:
            step("set_webhook", False, error=str(exc))
            return {"ok": False, "error": f"Error configurando webhook: {exc}", "steps": steps}

        # 8. Verificar webhook
        try:
            wh_info = self._tg_get("getWebhookInfo", bot_token).get("result", {})
            configured = bool(wh_info.get("url"))
            step("verify_webhook", configured, {"url": wh_info.get("url", ""), "configured": configured})
        except Exception as exc:
            step("verify_webhook", False, error=str(exc))

        return {
            "ok": True,
            "message": f"Fabrica '{factory_name}' desplegada y lista",
            "data": {
                "mode": "cloud",
                "factory_name": factory_name,
                "package_dir": package_dir,
                "api_module": api_module,
                "repo": f"https://github.com/{repo_full_name}",
                "service_url": service_url,
                "webhook_url": webhook_url,
                "bot_username": bot_info.get("username"),
                "steps": steps,
            },
        }

    # ------------------------------------------------------------------ #
    # Helpers Telegram                                                     #
    # ------------------------------------------------------------------ #

    def _tg_get(self, method: str, token: str) -> dict:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/{method}", method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    def _tg_set_webhook(self, token: str, url: str) -> None:
        data = json.dumps({"url": url}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/setWebhook",
            data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read().decode())
        if not result.get("ok"):
            raise ValueError(result.get("description", "setWebhook fallo"))

    # ------------------------------------------------------------------ #
    # Helpers GitHub                                                       #
    # ------------------------------------------------------------------ #

    def _gh(self, method: str, path: str, payload=None) -> dict:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN no configurada")
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"https://api.github.com{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}

    def _gh_create_repo(self, name: str, org: str) -> str:
        path = f"/orgs/{org}/repos" if org else "/user/repos"
        result = self._gh("POST", path, {"name": name, "auto_init": True, "private": False})
        return result["full_name"]

    def _gh_copy_all(self, src_repo: str, dst_repo: str, branch: str) -> int:
        files = self._gh_list_files_recursive(src_repo, "")
        count = 0
        for f in files:
            try:
                raw = self._gh("GET", f"/repos/{src_repo}/contents/{f['path']}")
                content_b64 = raw["content"].replace("\n", "")
                sha = self._gh_get_sha(dst_repo, f["path"], branch)
                payload: dict = {"message": f"init: {f['path']}", "content": content_b64}
                if sha:
                    payload["sha"] = sha
                if branch:
                    payload["branch"] = branch
                self._gh("PUT", f"/repos/{dst_repo}/contents/{f['path']}", payload)
                count += 1
            except Exception:
                pass
        return count

    def _gh_list_files_recursive(self, repo: str, path: str) -> list[dict]:
        try:
            items = self._gh("GET", f"/repos/{repo}/contents/{path}")
            if not isinstance(items, list):
                return [items] if items.get("type") == "file" else []
            result = []
            for item in items:
                if item["type"] == "file":
                    result.append(item)
                elif item["type"] == "dir":
                    result.extend(self._gh_list_files_recursive(repo, item["path"]))
            return result
        except Exception:
            return []

    def _gh_get_sha(self, repo: str, path: str, branch: str) -> str | None:
        try:
            url = f"/repos/{repo}/contents/{path}"
            if branch:
                url += f"?ref={branch}"
            return self._gh("GET", url).get("sha")
        except Exception:
            return None

    def _gh_filter_registry(self, repo: str, branch: str, verticals: list[str], package_dir: str) -> None:
        raw = self._gh("GET", f"/repos/{repo}/contents/{package_dir}/skills/registry.json")
        full = json.loads(base64.b64decode(raw["content"].replace("\n", "")).decode())
        filtered = {k: v for k, v in full.items() if v.get("vertical") in verticals}
        content_b64 = base64.b64encode(json.dumps(filtered, indent=2, ensure_ascii=False).encode()).decode()
        payload: dict = {"message": "factory: filter registry by verticals",
                         "content": content_b64, "sha": raw["sha"]}
        if branch:
            payload["branch"] = branch
        self._gh("PUT", f"/repos/{repo}/contents/{package_dir}/skills/registry.json", payload)

    # ------------------------------------------------------------------ #
    # Helpers Render                                                       #
    # ------------------------------------------------------------------ #

    def _render(self, method: str, path: str, payload=None) -> dict:
        token = os.getenv("RENDER_API_KEY")
        if not token:
            raise ValueError("RENDER_API_KEY no configurada")
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"https://api.render.com/v1{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}

    def _render_create(self, name: str, repo: str, owner_id: str,
                       branch: str, env_vars: dict, api_module: str) -> dict:
        payload = {
            "type": "web_service",
            "name": name,
            "ownerId": owner_id,
            "repo": repo,
            "autoDeploy": "yes",
            "serviceDetails": {
                "runtime": "python",
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": f"uvicorn {api_module} --host 0.0.0.0 --port $PORT",
                "plan": "free",
                "region": "oregon",
                "branch": branch,
                "envVars": [{"key": k, "value": v} for k, v in env_vars.items()],
            },
        }
        result = self._render("POST", "/services", payload)
        return result.get("service", result)

    def _render_wait(self, service_id: str, max_wait: int) -> tuple[str, str]:
        interval = 20
        elapsed = 0
        while True:
            deploys = self._render("GET", f"/services/{service_id}/deploys?limit=1")
            if deploys:
                deploy = deploys[0].get("deploy", deploys[0])
                status = deploy.get("status", "")
                if status in RENDER_TERMINAL:
                    if status != "live":
                        raise ValueError(f"Deploy termino con estado: {status}")
                    svc = self._render("GET", f"/services/{service_id}")
                    url = svc.get("serviceDetails", {}).get("url", "")
                    if not url:
                        url = f"https://{service_id}.onrender.com"
                    return url, status
            if elapsed >= max_wait:
                raise TimeoutError(f"Deploy no termino en {max_wait}s")
            time.sleep(interval)
            elapsed += interval

    # ------------------------------------------------------------------ #
    # .env.example generator                                              #
    # ------------------------------------------------------------------ #

    def _env_example(self, verticals: list[str], context: dict) -> str:
        seen: set[str] = set()
        admin_bot_token_env = context.get("admin_bot_token_env", "ADMIN_BOT_TOKEN")
        admin_chat_id_env = context.get("admin_chat_id_env", "ADMIN_CHAT_ID")
        lines = ["# Generated by new_factory", "# Do not commit real values", ""]
        lines += ["# Base", "ANTHROPIC_API_KEY=", ""]
        seen.add("ANTHROPIC_API_KEY")
        for v in verticals:
            vars_for_v = VERTICAL_ENV_VARS.get(v, [])
            vars_for_v = [
                admin_bot_token_env if var == "ADMIN_BOT_TOKEN" else
                admin_chat_id_env if var == "ADMIN_CHAT_ID" else
                var
                for var in vars_for_v
            ]
            new_vars = [var for var in vars_for_v if var not in seen]
            if new_vars:
                lines.append(f"# {v}")
                lines.extend(f"{var}=" for var in new_vars)
                lines.append("")
                seen.update(new_vars)
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Generic output helpers                                               #
    # ------------------------------------------------------------------ #

    def _copy_tree_rewritten(self, src: Path, dst: Path, source_package_dir: str, package_dir: str) -> None:
        if not src.exists():
            return
        shutil.copytree(
            str(src),
            str(dst),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        self._rewrite_tree(dst, source_package_dir, package_dir)

    def _copy_optional_file_rewritten(self, src: Path, dst: Path, source_package_dir: str, package_dir: str) -> None:
        if not src.exists():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if self._is_text_path(src):
            text = self._read_text(src)
            dst.write_text(self._rewrite_text(text, source_package_dir, package_dir), encoding="utf-8")
        else:
            shutil.copy(str(src), str(dst))

    def _rewrite_tree(self, root: Path, source_package_dir: str, package_dir: str) -> None:
        for path in root.rglob("*"):
            if path.is_file() and self._is_text_path(path):
                text = path.read_text(encoding="utf-8", errors="replace")
                path.write_text(self._rewrite_text(text, source_package_dir, package_dir), encoding="utf-8")

    def _rewrite_data(self, value, source_package_dir: str, package_dir: str):
        if isinstance(value, dict):
            return {key: self._rewrite_data(item, source_package_dir, package_dir) for key, item in value.items()}
        if isinstance(value, list):
            return [self._rewrite_data(item, source_package_dir, package_dir) for item in value]
        if isinstance(value, str):
            return self._rewrite_text(value, source_package_dir, package_dir)
        return value

    def _rewrite_text(self, text: str, source_package_dir: str, package_dir: str) -> str:
        replacements = [
            ("ADMIN_BOT_TOKEN", "ADMIN_BOT_TOKEN"),
            ("ADMIN_CHAT_ID", "ADMIN_CHAT_ID"),
            ("factory_api", "factory_api"),
            ("factory_admin", "factory_admin"),
            ("Factory", "Factory"),
            ("Factory", "Factory"),
            ("FACTORY", "FACTORY"),
            ("", ""),
            ("factory", "factory"),
            ("factory", "factory"),
            ("factory", "factory"),
            (source_package_dir, package_dir),
            ("main", "main"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _is_text_path(self, path: Path) -> bool:
        if path.name.endswith(".env.example"):
            return True
        return path.suffix.lower() in TEXT_SUFFIXES

    def _read_text(self, path: Path) -> str:
        data = path.read_bytes()
        if b"\x00" in data[:200]:
            for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
                try:
                    return data.decode(encoding)
                except UnicodeDecodeError:
                    continue
        return data.decode("utf-8", errors="replace")

    def _write_readme(self, target_root: Path, factory_name: str, package_dir: str, api_module: str) -> None:
        text = "\n".join([
            f"# {factory_name}",
            "",
            "Generated factory runtime.",
            "",
            "## Run",
            "",
            "```bash",
            f"uvicorn {api_module} --host 0.0.0.0 --port $PORT",
            "```",
            "",
            "## Structure",
            "",
            f"- `{package_dir}/engine`: runtime loaders and runners",
            f"- `{package_dir}/skills`: registered skills",
            f"- `{package_dir}/agents`: registered agents",
            f"- `{package_dir}/bots`: registered bots",
            "",
        ])
        (target_root / "README.md").write_text(text, encoding="utf-8")
