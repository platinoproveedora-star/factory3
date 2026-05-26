from __future__ import annotations

import json
from pathlib import Path


class UpworkCaseStudyGeneratorService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("portfolio_root") or "companies/EMP_FREELANCE_GROWTH/portfolio")
        data = self._read_json(root / "projects.json")
        projects = data.get("projects", [])
        project_id = context.get("project_id")
        if project_id:
            projects = [p for p in projects if p.get("id") == project_id]
        if not projects:
            return {"ok": False, "error": "No hay proyectos para generar case studies"}

        case_studies = [self._case_study(p) for p in projects]
        output = {"case_studies": case_studies}
        if context.get("save", True):
            out = root / "upwork" / "case_studies.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("\n\n---\n\n".join(case_studies), encoding="utf-8")
            output["saved_to"] = str(out)
        return {"ok": True, "data": output}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _case_study(self, project: dict) -> str:
        outcomes = "\n".join(f"- {x}" for x in project.get("outcomes", []))
        stack = ", ".join(project.get("stack", []))
        return (
            f"# {project.get('name', 'Project')}\n\n"
            f"**Type:** {project.get('type', 'Automation project')}\n\n"
            f"## Client Problem\n{project.get('problem', 'The client needed a more efficient operating workflow.')}\n\n"
            f"## Solution\n{project.get('solution', 'Built an automation system tailored to the workflow.')}\n\n"
            f"## Tools Used\n{stack or 'Python, APIs, dashboard and database tooling'}\n\n"
            f"## Results\n{outcomes or '- Created a working, reusable automation foundation.'}\n\n"
            f"## Why It Matters\nThis project shows the ability to move from business context to a working system: data structure, automation logic, dashboard visibility and a path to iterate."
        )
