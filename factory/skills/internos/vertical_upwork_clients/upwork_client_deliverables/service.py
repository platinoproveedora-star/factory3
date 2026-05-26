from __future__ import annotations

import json
from pathlib import Path


class UpworkClientDeliverablesService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("clients_root") or "companies/EMP_FREELANCE_GROWTH/clients")
        client_id = context.get("client_id")
        if not client_id:
            return {"ok": False, "error": "client_id requerido"}
        folder = root / client_id
        client = self._read_json(folder / "client.json")
        project = self._read_json(folder / "project.json")
        if not client or not project:
            return {"ok": False, "error": "client.json y project.json requeridos"}
        deliverables = context.get("deliverables") or project.get("deliverables") or []
        project["deliverables"] = deliverables
        text = self._render(client, project)
        if not context.get("dry_run", False):
            (folder / "deliverables.md").write_text(text, encoding="utf-8")
            (folder / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "data": {"deliverables_md": text, "path": str(folder / "deliverables.md")}}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _render(self, client: dict, project: dict) -> str:
        items = "\n".join(f"- [ ] {item}" for item in project.get("deliverables", []))
        return (
            f"# Deliverables - {project.get('project_name')}\n\n"
            f"Client: {client.get('client_name')} (`{client.get('client_id')}`)\n\n"
            f"## Scope\n{project.get('scope') or 'Por definir'}\n\n"
            f"## Deliverables\n{items}\n\n"
            "## Handoff Notes\n- No secrets should be committed.\n- Deployment credentials stay in Render/Supabase/GitHub settings.\n- Final repo transfer requires client GitHub username or organization.\n"
        )
