from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class UpworkClientCloseService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("clients_root") or "companies/EMP_FREELANCE_GROWTH/clients")
        client_id = context.get("client_id")
        if not client_id:
            return {"ok": False, "error": "client_id requerido"}
        folder = root / client_id
        client = self._read_json(folder / "client.json")
        project_folder = self._project_folder(folder, context.get("project_code"))
        project = self._read_json(project_folder / "project.json")
        if not client:
            return {"ok": False, "error": "client.json no encontrado"}
        now = datetime.utcnow().isoformat() + "Z"
        client["status"] = context.get("client_status", "delivered")
        client["updated_at"] = now
        project["status"] = context.get("project_status", "delivered")
        project["updated_at"] = now
        closeout = self._render(client, project, context)
        if not context.get("dry_run", False):
            (folder / "client.json").write_text(json.dumps(client, ensure_ascii=False, indent=2), encoding="utf-8")
            if project:
                (project_folder / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
            (project_folder / "closeout.md").write_text(closeout, encoding="utf-8")
            self._update_registry(root / "registry.json", client)
        return {"ok": True, "data": {"client": client, "project": project, "closeout_md": closeout, "path": str(project_folder / "closeout.md")}}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _update_registry(self, path: Path, client: dict) -> None:
        reg = self._read_json(path) or {"next_number": 101, "clients": []}
        for item in reg.get("clients", []):
            if item.get("client_id") == client.get("client_id"):
                item["status"] = client.get("status")
        path.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")

    def _render(self, client: dict, project: dict, context: dict) -> str:
        return (
            f"# Closeout - {project.get('project_name', client.get('client_name'))}\n\n"
            f"Client: {client.get('client_name')} (`{client.get('client_id')}`)\n"
            f"Closed at: {datetime.utcnow().isoformat()}Z\n\n"
            "## Final Checklist\n"
            "- [ ] Deliverables accepted\n"
            "- [ ] README updated\n"
            "- [ ] Secrets removed from repo\n"
            "- [ ] Deploy URLs shared\n"
            "- [ ] Client confirmed GitHub owner if transfer applies\n\n"
            f"## Notes\n{context.get('notes', '')}\n"
        )

    def _project_folder(self, client_folder: Path, project_code: str | None) -> Path:
        if project_code:
            return client_folder / "projects" / project_code
        projects_root = client_folder / "projects"
        if projects_root.exists():
            projects = sorted([p for p in projects_root.iterdir() if p.is_dir()])
            if projects:
                return projects[0]
        return client_folder
