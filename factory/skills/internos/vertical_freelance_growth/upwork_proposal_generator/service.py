from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


class UpworkProposalGeneratorService:
    def ejecutar(self, context: dict) -> dict:
        job = (context.get("job_description") or context.get("job") or "").strip()
        if not job:
            return {"ok": False, "error": "job_description requerido"}
        root = Path(context.get("portfolio_root") or "companies/EMP_FREELANCE_GROWTH/portfolio")
        profile = self._read_json(root / "profile.json")
        projects = self._read_json(root / "projects.json").get("projects", [])
        matches = self._match_projects(job, projects)
        proposal = self._proposal(job, profile, matches)
        output = {"proposal": proposal, "matched_projects": [p.get("id") for p in matches]}
        if context.get("save", True):
            out_dir = root / "upwork" / "proposals"
            out_dir.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", job.lower())[:45].strip("-") or "proposal"
            out = out_dir / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{slug}.md"
            out.write_text(proposal, encoding="utf-8")
            output["saved_to"] = str(out)
        return {"ok": True, "data": output}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _match_projects(self, job: str, projects: list[dict]) -> list[dict]:
        words = {w.lower() for w in re.findall(r"[a-zA-Z0-9_]+", job) if len(w) > 3}
        scored = []
        for project in projects:
            text = json.dumps(project, ensure_ascii=False).lower()
            score = sum(1 for word in words if word in text)
            scored.append((score, project))
        return [p for score, p in sorted(scored, key=lambda item: item[0], reverse=True)[:2] if score > 0] or projects[:2]

    def _proposal(self, job: str, profile: dict, matches: list[dict]) -> str:
        name = profile.get("name") or "Alfredo"
        project_lines = "\n".join(
            f"- {p.get('name')}: {p.get('type')} - {p.get('solution')}" for p in matches
        )
        return (
            f"Hi, I can help you build this.\n\n"
            f"I specialize in practical AI automation systems: chat agents, lead capture, dashboards, API integrations and business workflows that can be tested quickly and improved over time.\n\n"
            f"Relevant work:\n{project_lines}\n\n"
            f"For your project, I would start by clarifying the workflow, data to capture, required integrations and success metrics. Then I would build a first working version with clean structure, so you can test it with real users instead of only reviewing mockups.\n\n"
            f"My suggested first milestone:\n"
            f"1. Confirm the user flow and data model.\n"
            f"2. Build the MVP automation or dashboard.\n"
            f"3. Connect storage/integrations.\n"
            f"4. Test with real examples and document how to operate it.\n\n"
            f"I can keep the communication simple and business-focused, while still handling the technical build end to end.\n\n"
            f"Best,\n{name}\n\n"
            f"---\nJob notes used:\n{job[:1200]}"
        )
