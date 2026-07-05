from __future__ import annotations

import json
from pathlib import Path


class Apps4AllOpsStatusSnapshotService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        raw_project = str(context.get("project_path") or "").strip()
        module_code = str(context.get("module_code") or "").strip()
        project_path = repo_root / raw_project if raw_project and not Path(raw_project).is_absolute() else Path(raw_project)
        files = {}
        if raw_project and project_path.exists():
            for rel in ["project.json", ".env.example", "package.json", "middleware.ts", "lib/auth.ts"]:
                files[rel] = (project_path / rel).exists()
            project_json = self._read_json(project_path / "project.json")
        else:
            project_json = {}
        snapshot = {
            "module_code": module_code or project_json.get("module_code"),
            "project_path": raw_project,
            "project_files": files,
            "marketplace_expected": True,
            "billing_expected": bool(context.get("billing_expected", True)),
            "remote_smoke_expected": bool(context.get("remote_smoke_expected", True)),
            "writes_performed": False,
        }
        return {"ok": True, "data": snapshot}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}
