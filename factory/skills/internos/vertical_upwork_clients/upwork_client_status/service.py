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
            project = self._read_json(folder / "project.json")
            rows.append({
                "client_id": item.get("client_id"),
                "client_name": client.get("client_name") or item.get("client_name"),
                "client_status": client.get("status") or item.get("status"),
                "project_name": project.get("project_name", ""),
                "project_status": project.get("status", ""),
                "budget": project.get("budget", ""),
                "deadline": project.get("deadline", ""),
                "repo": project.get("repo") or project.get("repo_name", ""),
                "folder": str(folder).replace("\\", "/"),
            })
        return {"ok": True, "data": {"clients": rows, "count": len(rows), "registry": registry}}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
