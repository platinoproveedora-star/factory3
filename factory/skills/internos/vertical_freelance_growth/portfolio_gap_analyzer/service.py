from __future__ import annotations

import json
from pathlib import Path


class PortfolioGapAnalyzerService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("portfolio_root") or "companies/EMP_FREELANCE_GROWTH/portfolio")
        projects = self._read_json(root / "projects.json").get("projects", [])
        audit = self._read_json(root / "factory_audit.json")
        rows = [self._project_gap(p) for p in projects]
        for candidate in audit.get("portfolio_candidates", []):
            rows.append(self._candidate_gap(candidate))

        data = {
            "summary": {
                "total_items": len(rows),
                "ready_count": sum(1 for row in rows if row["readiness_score"] >= 80),
                "needs_assets_count": sum(1 for row in rows if "assets" in row["missing_groups"]),
            },
            "items": rows,
            "top_recommendations": self._top_recommendations(rows),
        }
        if context.get("save", True):
            out = root / "portfolio_gaps.md"
            out.write_text(self._markdown(data), encoding="utf-8")
            data["saved_to"] = str(out)
        return {"ok": True, "data": data}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _project_gap(self, project: dict) -> dict:
        missing = []
        score = 45
        for field in ["problem", "solution", "stack", "outcomes"]:
            if project.get(field):
                score += 8
            else:
                missing.append(field)
        recommendations = [
            "Agregar 2 screenshots: overview y flujo principal.",
            "Grabar video demo de 45-90 segundos.",
            "Agregar link publico si existe o nota de demo privada.",
        ]
        if "real" in " ".join(project.get("outcomes", [])).lower():
            score += 8
        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "kind": "existing_project",
            "readiness_score": min(score, 78),
            "missing_groups": ["assets", "video"] + missing,
            "recommendations": recommendations,
        }

    def _candidate_gap(self, item: dict) -> dict:
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "kind": "audit_candidate",
            "readiness_score": 55,
            "missing_groups": ["add_to_projects_json", "assets", "case_study", "video"],
            "recommendations": [
                "Agregar este candidato a projects.json si es vendible.",
                *item.get("asset_recommendations", []),
                "Generar case study despues de agregarlo al portafolio.",
            ],
        }

    def _top_recommendations(self, rows: list[dict]) -> list[str]:
        return [
            "Priorizar proyectos con dashboards vivos para videos cortos.",
            "Agregar Freelance Center como proyecto vendible si aparece como candidato.",
            "Crear screenshots con datos sensibles ocultos antes de publicar en Upwork/Pioneer.",
            "Actualizar case studies despues de cada auditoria relevante.",
        ]

    def _markdown(self, data: dict) -> str:
        lines = ["# Portfolio Gap Analysis", "", "## Summary", ""]
        for key, value in data["summary"].items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Items", ""])
        for item in data["items"]:
            lines.extend([
                f"### {item['name']}",
                f"- ID: `{item['id']}`",
                f"- Kind: {item['kind']}",
                f"- Readiness: {item['readiness_score']}/100",
                f"- Missing: {', '.join(item['missing_groups'])}",
                "- Recommendations:",
            ])
            lines.extend([f"  - {r}" for r in item["recommendations"]])
            lines.append("")
        return "\n".join(lines)
