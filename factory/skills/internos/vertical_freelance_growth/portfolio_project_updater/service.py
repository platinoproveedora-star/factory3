from __future__ import annotations

import json
from pathlib import Path


class PortfolioProjectUpdaterService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("portfolio_root") or "companies/EMP_FREELANCE_GROWTH/portfolio")
        projects_path = root / "projects.json"
        data = self._read_json(projects_path) or {"projects": []}
        audit = context.get("audit") or self._read_json(root / "factory_audit.json")
        candidate_ids = set(context.get("candidate_ids") or [])
        add_all = bool(context.get("add_all", False))
        added = []

        existing = {p.get("id") for p in data.get("projects", [])}
        for candidate in audit.get("portfolio_candidates", []):
            if not add_all and candidate.get("id") not in candidate_ids:
                continue
            if candidate.get("id") in existing:
                continue
            data["projects"].append(self._candidate_to_project(candidate))
            existing.add(candidate.get("id"))
            added.append(candidate.get("id"))

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"added": added, "projects": data.get("projects", [])}}

        projects_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "data": {"added": added, "saved_to": str(projects_path), "count": len(data.get("projects", []))}}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _candidate_to_project(self, candidate: dict) -> dict:
        return {
            "id": candidate.get("id"),
            "name": candidate.get("name"),
            "type": candidate.get("type"),
            "problem": candidate.get("problem"),
            "solution": candidate.get("solution"),
            "stack": candidate.get("stack") or [],
            "outcomes": candidate.get("outcomes") or [],
            "portfolio_notes": {
                "source": candidate.get("source"),
                "evidence": candidate.get("evidence") or [],
                "portfolio_value": candidate.get("portfolio_value"),
                "asset_recommendations": candidate.get("asset_recommendations") or [],
            },
        }
