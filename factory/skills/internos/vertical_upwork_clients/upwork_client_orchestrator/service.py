from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factory.engine.skill_loader import SkillLoader
from factory.engine.skill_runner import SkillRunner


class UpworkClientOrchestratorService:
    def ejecutar(self, context: dict) -> dict:
        brief = (context.get("brief") or context.get("text") or context.get("job_text") or "").strip()
        parsed = self._parse_brief(brief)
        client_name = context.get("client_name") or parsed["client_name"]
        project_name = context.get("project_name") or parsed["project_name"]
        scope = context.get("scope") or parsed["scope"]
        budget = context.get("budget") or parsed["budget"]
        deadline = context.get("deadline") or parsed["deadline"]
        clients_root = context.get("clients_root") or "companies/EMP_FREELANCE_GROWTH/clients"
        dry_run = bool(context.get("dry_run", False))

        runner = SkillRunner(SkillLoader(ROOT / "factory" / "skills" / "internos"))
        client_res = runner.run("vertical_upwork_clients/upwork_client_init", {
            "clients_root": clients_root,
            "client_name": client_name,
            "company_name": context.get("company_name", ""),
            "contact_email": context.get("contact_email", parsed["email"]),
            "platform": context.get("platform", "upwork"),
            "notes": brief[:2000],
            "dry_run": dry_run,
        })
        if not client_res.get("ok"):
            return client_res
        client_id = client_res["data"]["client_id"]
        repo_name = context.get("repo_name") or f"{client_id.lower()}-{self._slug(project_name)}"
        repo_result = None
        repo_full = ""
        if context.get("create_repo"):
            repo_result = runner.run("github_create_repo", {
                "name": repo_name,
                "description": f"{client_id} - {project_name}",
                "private": context.get("repo_private", True),
                "auto_init": True,
                "dry_run": dry_run,
            })
            if repo_result.get("ok"):
                repo_full = (repo_result.get("data") or {}).get("full_name", "")

        project_res = runner.run("vertical_upwork_clients/upwork_client_project_init", {
            "clients_root": clients_root,
            "client_id": client_id,
            "project_name": project_name,
            "scope": scope,
            "budget": budget,
            "deadline": deadline,
            "platform": context.get("platform", "upwork"),
            "repo": repo_full,
            "repo_name": repo_name,
            "source_brief": brief,
            "dry_run": dry_run,
        })
        if not project_res.get("ok"):
            return project_res

        return {"ok": True, "data": {
            "client": client_res.get("data"),
            "project": project_res.get("data"),
            "repo": repo_result,
            "parsed": parsed,
            "next_steps": [
                "Revisar client.json y project.json",
                "Completar deliverables.md",
                "Crear repo si no se creo automaticamente",
                "Definir primer milestone y fecha de entrega",
            ],
        }}

    def _parse_brief(self, text: str) -> dict:
        email = self._first(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        budget = self._first(r"(?i)(?:budget|presupuesto)[:\s]*([$]?\s?[0-9,]+(?:\s?-\s?[$]?\s?[0-9,]+)?)", text)
        deadline = self._first(r"(?i)(?:timeline|deadline|fecha|entrega)[:\s]*([^\n]{3,80})", text)
        lines = [line.strip("-* \t") for line in text.splitlines() if line.strip()]
        project_name = lines[0][:80] if lines else "Proyecto Upwork"
        client_name = "Cliente Upwork"
        for line in lines:
            if re.search(r"(?i)(client|cliente|company|empresa)", line):
                client_name = re.sub(r"(?i)(client|cliente|company|empresa)[:\s]*", "", line).strip()[:80] or client_name
                break
        scope = text[:2500] if text else "Scope por definir"
        return {"client_name": client_name, "project_name": project_name, "scope": scope, "budget": budget, "deadline": deadline, "email": email}

    def _first(self, pattern: str, text: str) -> str:
        m = re.search(pattern, text or "")
        return m.group(1).strip() if m else ""

    def _slug(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "project"
