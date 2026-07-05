from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
REQUIRED_FILES = [
    "project.json",
    "package.json",
    "middleware.ts",
    "lib/auth.ts",
    "lib/factory.ts",
    "lib/platform.ts",
    "app/api/auth/login/route.ts",
    "app/api/auth/logout/route.ts",
    "app/api/auth/me/route.ts",
]
REQUIRED_PROJECT_FIELDS = ["company_id", "project_code", "module_code", "schema", "platform"]


class Apps4AllDashHealthCheckService:
    def ejecutar(self, context: dict) -> dict:
        raw_path = context.get("project_path") or context.get("target_path")
        if not raw_path:
            return {"ok": False, "error": "project_path requerido"}
        project_path = Path(str(raw_path))
        if not project_path.is_absolute():
            project_path = ROOT / project_path
        if not project_path.exists():
            return {"ok": False, "error": "project_path no existe"}

        findings = []
        for rel in REQUIRED_FILES:
            if not (project_path / rel).exists():
                findings.append({"severity": "blocker", "kind": "missing_file", "path": rel})

        project = self._project(project_path / "project.json")
        for field in REQUIRED_PROJECT_FIELDS:
            if not project.get(field):
                findings.append({"severity": "blocker", "kind": "missing_project_field", "field": field})

        text_hits = []
        for path in project_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".ts", ".tsx", ".json", ".md", ".example"}:
                rel = str(path.relative_to(project_path)).replace("\\", "/")
                if any(part in rel for part in ["node_modules/", ".next/"]):
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "coti4all" in text.lower() and not context.get("allow_template_residue"):
                    text_hits.append(rel)
        for rel in sorted(set(text_hits)):
            findings.append({"severity": "warning", "kind": "template_residue", "path": rel})

        blockers = [row for row in findings if row["severity"] == "blocker"]
        warnings = [row for row in findings if row["severity"] == "warning"]
        return {
            "ok": not blockers,
            "data": {
                "ready": not blockers,
                "summary": {"blockers": len(blockers), "warnings": len(warnings), "total": len(findings)},
                "blockers": blockers,
                "warnings": warnings,
                "project": project,
            },
            "error": f"{len(blockers)} blockers" if blockers else None,
        }

    def _project(self, path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
