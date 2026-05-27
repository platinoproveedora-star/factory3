from __future__ import annotations

import json
from pathlib import Path


class UpworkClientStatusService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("clients_root") or "companies/EMP_FREELANCE_GROWTH/clients")
        registry = self._read_json(root / "registry.json") or {"clients": []}
        rows = []
        for item in registry.get("clients", []):
            folder = root / item.get("client_id", "")
            client = self._read_json(folder / "client.json")
            projects = self._projects(folder)
            if not projects:
                rows.append({
                    "client_id": item.get("client_id"),
                    "client_name": client.get("client_name") or item.get("client_name"),
                    "client_status": client.get("status") or item.get("status"),
                    "project_code": "",
                    "project_name": "",
                    "project_status": "",
                    "budget": "",
                    "deadline": "",
                    "repo": "",
                    "folder": str(folder).replace("\\", "/"),
                    "project_folder": "",
                })
                continue
            for project, project_folder in projects:
                rows.append({
                "client_id": item.get("client_id"),
                "client_name": client.get("client_name") or item.get("client_name"),
                "client_status": client.get("status") or item.get("status"),
                "project_code": project.get("project_code", ""),
                "project_name": project.get("project_name", ""),
                "project_status": project.get("status", ""),
                "budget": project.get("budget", ""),
                "deadline": project.get("deadline", ""),
                "repo": project.get("repo") or project.get("repo_name", ""),
                "folder": str(folder).replace("\\", "/"),
                "project_folder": str(project_folder).replace("\\", "/"),
                })
        return {"ok": True, "data": {"clients": rows, "count": len(rows), "registry": registry}}

    def _projects(self, folder: Path) -> list[tuple[dict, Path]]:
        projects = []
        legacy = self._read_json(folder / "project.json")
        if legacy:
            projects.append((legacy, folder))
        projects_root = folder / "projects"
        if projects_root.exists():
            for project_folder in sorted([p for p in projects_root.iterdir() if p.is_dir()]):
                project = self._read_json(project_folder / "project.json")
                if project:
                    projects.append((project, project_folder))
        return projects

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
