from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


class UpworkClientProjectInitService:
    def ejecutar(self, context: dict) -> dict:
        clients_root = Path(context.get("clients_root") or "companies/EMP_FREELANCE_GROWTH/clients")
        client_id = context.get("client_id")
        if not client_id:
            return {"ok": False, "error": "client_id requerido"}
        folder = clients_root / client_id
        if not folder.exists() and not context.get("dry_run", False):
            return {"ok": False, "error": f"cliente no existe: {client_id}"}
        project_code = (context.get("project_code") or self._next_project_code(folder)).strip().upper()
        project_folder = folder / "projects" / project_code
        project_name = (context.get("project_name") or project_code).strip()
        repo_name = context.get("repo_name") or self._repo_name(client_id, project_code)
        now = datetime.utcnow().isoformat() + "Z"
        project = {
            "client_id": client_id,
            "project_code": project_code,
            "project_name": project_name,
            "status": context.get("status", "planned"),
            "scope": context.get("scope", ""),
            "budget": context.get("budget", ""),
            "deadline": context.get("deadline", ""),
            "platform": context.get("platform", "upwork"),
            "repo": context.get("repo", ""),
            "repo_name": repo_name,
            "folder": str(project_folder).replace("\\", "/"),
            "deliverables": context.get("deliverables") or self._deliverables_from_scope(context.get("scope", "")),
            "source_brief": context.get("source_brief", ""),
            "created_at": now,
            "updated_at": now,
        }
        if not context.get("dry_run", False):
            project_folder.mkdir(parents=True, exist_ok=True)
            (project_folder / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
            (project_folder / "deliverables.md").write_text(self._deliverables_md(project), encoding="utf-8")
            notes = project_folder / "notes.md"
            if not notes.exists():
                notes.write_text(f"# Notes - {project_code}\n\n", encoding="utf-8")
            (project_folder / "assets").mkdir(exist_ok=True)
            time_log = project_folder / "time_log.json"
            if not time_log.exists():
                time_log.write_text(json.dumps(self._time_log(project), ensure_ascii=False, indent=2), encoding="utf-8")
            closeout = project_folder / "closeout.md"
            if not closeout.exists():
                closeout.write_text(self._closeout_md(project), encoding="utf-8")
        return {"ok": True, "data": {"project": project, "folder": str(project_folder)}}

    def _next_project_code(self, folder: Path) -> str:
        if not folder.exists():
            return "PROY-001"
        existing = []
        project = self._read_json(folder / "project.json")
        if project.get("project_code"):
            existing.append(project["project_code"])
        projects_root = folder / "projects"
        for path in projects_root.glob("PROY-*"):
            if path.is_dir():
                existing.append(path.name)
        numbers = []
        for code in existing:
            match = re.search(r"(\d+)$", str(code))
            if match:
                numbers.append(int(match.group(1)))
        return f"PROY-{(max(numbers) + 1 if numbers else 1):03d}"

    def _repo_name(self, client_id: str, project_code: str) -> str:
        client = re.sub(r"[^a-z0-9]+", "", client_id.lower())
        project = re.sub(r"[^a-z0-9]+", "", project_code.lower())
        return f"{client}-{project}"

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _deliverables_from_scope(self, scope: str) -> list[str]:
        base = ["Working MVP", "README / usage notes", "Deployment notes", "Final handoff checklist"]
        text = scope.lower()
        if "dashboard" in text:
            base.insert(1, "Dashboard")
        if "chat" in text or "bot" in text:
            base.insert(1, "Chat agent flow")
        if "lead" in text:
            base.insert(1, "Lead capture flow")
        return list(dict.fromkeys(base))

    def _deliverables_md(self, project: dict) -> str:
        items = "\n".join(f"- [ ] {item}" for item in project.get("deliverables", []))
        return f"# Deliverables - {project['project_code']} - {project['project_name']}\n\nClient: `{project['client_id']}`\nRepo: `{project.get('repo_name', '')}`\n\n## Scope\n{project.get('scope') or 'Por definir'}\n\n## Checklist\n{items}\n"

    def _closeout_md(self, project: dict) -> str:
        return f"# Closeout - {project['project_code']} - {project['project_name']}\n\n- [ ] Deliverables accepted\n- [ ] Secrets removed from repo\n- [ ] README updated\n- [ ] Deploy URL shared\n- [ ] Repo transfer requested if applicable\n"

    def _time_log(self, project: dict) -> dict:
        return {
            "client_id": project.get("client_id", ""),
            "project_code": project.get("project_code", ""),
            "started_at": "",
            "deadline": project.get("deadline", ""),
            "hour_blocks": [],
            "alerts": {"every_hours": 10, "enabled": True},
        }
