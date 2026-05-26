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
        project_name = (context.get("project_name") or "Proyecto por definir").strip()
        repo_name = context.get("repo_name") or f"{client_id.lower()}-{self._slug(project_name)}"
        now = datetime.utcnow().isoformat() + "Z"
        project = {
            "client_id": client_id,
            "project_name": project_name,
            "status": context.get("status", "planned"),
            "scope": context.get("scope", ""),
            "budget": context.get("budget", ""),
            "deadline": context.get("deadline", ""),
            "platform": context.get("platform", "upwork"),
            "repo": context.get("repo", ""),
            "repo_name": repo_name,
            "deliverables": context.get("deliverables") or self._deliverables_from_scope(context.get("scope", "")),
            "source_brief": context.get("source_brief", ""),
            "created_at": now,
            "updated_at": now,
        }
        if not context.get("dry_run", False):
            (folder / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
            (folder / "deliverables.md").write_text(self._deliverables_md(project), encoding="utf-8")
            closeout = folder / "closeout.md"
            if not closeout.exists():
                closeout.write_text(self._closeout_md(project), encoding="utf-8")
        return {"ok": True, "data": {"project": project, "folder": str(folder)}}

    def _slug(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "project"

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
        return f"# Deliverables - {project['project_name']}\n\nClient: `{project['client_id']}`\n\n## Scope\n{project.get('scope') or 'Por definir'}\n\n## Checklist\n{items}\n"

    def _closeout_md(self, project: dict) -> str:
        return f"# Closeout - {project['project_name']}\n\n- [ ] Deliverables accepted\n- [ ] Secrets removed from repo\n- [ ] README updated\n- [ ] Deploy URL shared\n- [ ] Repo transfer requested if applicable\n"
