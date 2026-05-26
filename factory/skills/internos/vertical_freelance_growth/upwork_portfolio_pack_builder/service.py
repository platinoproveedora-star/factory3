from __future__ import annotations

import json
from pathlib import Path


class UpworkPortfolioPackBuilderService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("portfolio_root") or "companies/EMP_FREELANCE_GROWTH/portfolio")
        projects = self._read_json(root / "projects.json").get("projects", [])
        if not projects:
            return {"ok": False, "error": "No hay proyectos en projects.json"}

        packs = [self._pack(project) for project in projects]
        output = {"packs": packs}
        if context.get("save", True):
            out = root / "upwork" / "portfolio_pack.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("\n\n---\n\n".join(pack["markdown"] for pack in packs), encoding="utf-8")
            output["saved_to"] = str(out)
        return {"ok": True, "data": output}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _pack(self, project: dict) -> dict:
        title = self._title(project)
        short = self._short(project)
        full = self._full(project)
        category = self._category(project)
        stack = project.get("stack", [])
        results = project.get("outcomes", [])
        assets = self._assets_needed(project)
        markdown = self._markdown(title, category, short, full, stack, results, assets)
        return {
            "id": project.get("id"),
            "title": title,
            "category": category,
            "short_description": short,
            "full_description": full,
            "stack": stack,
            "results": results,
            "assets_needed": assets,
            "markdown": markdown,
        }

    def _title(self, project: dict) -> str:
        name = project.get("name") or "Automation Project"
        type_ = (project.get("type") or "").lower()
        if "chat" in type_:
            return f"{name} - AI Chat Agent and Lead Capture System"
        if "campaign" in type_:
            return f"{name} - Campaign Landing Page and Operations Dashboard"
        if "hr" in type_ or "recruit" in type_:
            return f"{name} - Recruiting Operations Dashboard"
        if "logistics" in type_:
            return f"{name} - Fleet Operations Dashboard and Automation"
        return f"{name} - Business Automation System"

    def _short(self, project: dict) -> str:
        return (
            f"Built a practical {project.get('type', 'automation system')} to solve a real business workflow: "
            f"{project.get('problem', 'manual operations and limited visibility')}"
        )

    def _full(self, project: dict) -> str:
        return (
            f"The project started with a clear business problem: {project.get('problem')} "
            f"I designed and built a working solution: {project.get('solution')} "
            "The focus was not only to create a visual interface, but to connect the workflow with real data, reusable logic and a dashboard the business can operate."
        )

    def _category(self, project: dict) -> str:
        type_ = (project.get("type") or "").lower()
        if "chat" in type_:
            return "AI Chatbot / Customer Support Automation"
        if "dashboard" in type_:
            return "Data Visualization / Business Dashboard"
        if "campaign" in type_:
            return "Digital Marketing / Landing Page"
        return "Business Process Automation"

    def _assets_needed(self, project: dict) -> list[str]:
        base = [
            "1 dashboard screenshot with sensitive data hidden",
            "1 workflow diagram or simple before/after graphic",
            "Short Loom/video demo if available",
        ]
        pid = project.get("id")
        if pid == "emp_logplat_fleet_ops":
            return base + ["Screenshot of Overview/Viajes/Gastos sections", "Example of KPI cards"]
        if pid == "estoiko_chat_agents":
            return base + ["Screenshot of Telegram conversation", "Screenshot of leads dashboard"]
        if pid == "rstate_campaign":
            return base + ["Landing page screenshot", "Media upload/dashboard screenshot"]
        if pid == "rh1_recruiting_dashboard":
            return base + ["Pipeline dashboard screenshot", "Candidate/vacancy list screenshot"]
        return base

    def _markdown(self, title: str, category: str, short: str, full: str, stack: list, results: list, assets: list) -> str:
        stack_md = "\n".join(f"- {item}" for item in stack)
        results_md = "\n".join(f"- {item}" for item in results)
        assets_md = "\n".join(f"- {item}" for item in assets)
        return (
            f"# {title}\n\n"
            f"## Upwork Category\n{category}\n\n"
            f"## Short Description\n{short}\n\n"
            f"## Full Description\n{full}\n\n"
            f"## Stack\n{stack_md}\n\n"
            f"## Results\n{results_md}\n\n"
            f"## Assets To Add\n{assets_md}\n"
        )
