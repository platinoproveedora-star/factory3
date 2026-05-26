from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


class FactoryPortfolioAuditorService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("root") or ".").resolve()
        portfolio_root = Path(context.get("portfolio_root") or root / "companies/EMP_FREELANCE_GROWTH/portfolio")
        existing = self._existing_project_ids(portfolio_root / "projects.json")

        companies = self._scan_companies(root)
        dashboards = self._scan_dashboards(root)
        verticals = self._scan_verticals(root)
        docs = self._scan_docs(root)
        candidates = self._build_candidates(companies, dashboards, verticals, existing)
        recommendations = self._recommendations(candidates, dashboards, verticals)

        data = {
            "audited_at": datetime.utcnow().isoformat() + "Z",
            "companies": companies,
            "dashboards": dashboards,
            "verticals": verticals,
            "docs": docs,
            "portfolio_candidates": candidates,
            "recommendations": recommendations,
            "daily_agent_plan": {
                "time_local": "23:00",
                "actions": [
                    "Run factory_portfolio_auditor",
                    "Run portfolio_gap_analyzer",
                    "Open/update documentation tasks",
                    "Prepare projects.json update suggestions",
                ],
            },
        }

        if context.get("save", True):
            out_json = portfolio_root / "factory_audit.json"
            out_md = portfolio_root / "factory_audit.md"
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            out_md.write_text(self._markdown(data), encoding="utf-8")
            data["saved_to"] = {"json": str(out_json), "md": str(out_md)}

        return {"ok": True, "data": data}

    def _existing_project_ids(self, path: Path) -> set[str]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {str(p.get("id")) for p in data.get("projects", []) if p.get("id")}
        except Exception:
            return set()

    def _scan_companies(self, root: Path) -> list[dict]:
        folders = []
        for base in [root / "companies", root]:
            if not base.exists():
                continue
            for path in base.iterdir():
                if path.is_dir() and (path.name.startswith("EMP_") or path.name in {"EMP_LOGPLAT"}):
                    folders.append(path)
        seen = set()
        out = []
        for path in sorted(folders, key=lambda p: p.name):
            rel = self._rel(root, path)
            if rel in seen:
                continue
            seen.add(rel)
            out.append({
                "id": path.name,
                "path": rel,
                "has_dashboard": (path / "dashboard" / "app.py").exists(),
                "has_readme": (path / "README.md").exists() or (path / f"{path.name}.md").exists(),
                "has_schema": bool(list(path.glob("*schema*.sql"))),
                "has_landing": (path / "landing" / "index.html").exists(),
            })
        return out

    def _scan_dashboards(self, root: Path) -> list[dict]:
        dashboards = []
        for app in sorted(root.glob("**/dashboard/app.py")):
            rel = self._rel(root, app)
            if ".venv" in rel or "__pycache__" in rel:
                continue
            company = self._company_from_path(app)
            dashboards.append({
                "company_id": company,
                "path": rel,
                "render_yaml": self._rel(root, app.parent / "render.yaml") if (app.parent / "render.yaml").exists() else "",
                "requirements": self._rel(root, app.parent / "requirements.txt") if (app.parent / "requirements.txt").exists() else "",
                "signals": self._dashboard_signals(app),
            })
        return dashboards

    def _scan_verticals(self, root: Path) -> list[dict]:
        base = root / "factory/skills/internos"
        out = []
        if not base.exists():
            return out
        for path in sorted(base.glob("vertical_*")):
            if not path.is_dir():
                continue
            skills = [p.name for p in path.iterdir() if p.is_dir()]
            out.append({"vertical": path.name, "path": self._rel(root, path), "skills_count": len(skills), "skills": skills[:20]})
        return out

    def _scan_docs(self, root: Path) -> dict:
        docs = root / "docs"
        files = sorted(docs.glob("*.md")) if docs.exists() else []
        return {
            "docs_count": len(files),
            "vertical_docs": [self._rel(root, p) for p in files if p.name.startswith("VERTICAL_")],
            "registries": [self._rel(root, p) for p in files if p.name in {"TABLES.md", "DASHBOARDS.md", "DOCS.md"}],
        }

    def _build_candidates(self, companies: list[dict], dashboards: list[dict], verticals: list[dict], existing: set[str]) -> list[dict]:
        candidates = []
        represented_companies = self._represented_companies(existing)
        for dash in dashboards:
            company = dash["company_id"]
            if company in represented_companies:
                continue
            if company == "EMP_FREELANCE_GROWTH":
                continue
            project_id = self._project_id(company, dash["path"])
            if project_id in existing:
                continue
            title = self._title(company, dash)
            candidates.append({
                "id": project_id,
                "name": title,
                "source": "dashboard",
                "company_id": company,
                "evidence": [dash["path"], dash.get("render_yaml", "")],
                "type": self._type_from_signals(dash["signals"]),
                "problem": self._problem_from_company(company, dash["signals"]),
                "solution": self._solution_from_signals(company, dash["signals"]),
                "stack": self._stack_from_signals(dash["signals"]),
                "outcomes": self._outcomes_from_signals(dash["signals"]),
                "portfolio_value": self._portfolio_value(company, dash["signals"]),
                "asset_recommendations": self._assets_for(dash["signals"]),
            })

        if any(v["vertical"] == "vertical_freelance_growth" for v in verticals) and "freelance_growth_system" not in existing:
            candidates.append({
                "id": "freelance_growth_system",
                "name": "Freelance Growth Operating System",
                "source": "vertical",
                "company_id": "EMP_FREELANCE_GROWTH",
                "evidence": ["factory/skills/internos/vertical_freelance_growth", "companies/EMP_FREELANCE_GROWTH/dashboard/app.py"],
                "type": "freelance sales operations system",
                "problem": "A new Upwork/Pioneer seller needs a repeatable way to turn real projects into profile copy, case studies, job analysis and proposals.",
                "solution": "Built a Freelance Center dashboard and reusable skills for profile generation, portfolio packaging, job scoring and proposal generation.",
                "stack": ["Python", "Streamlit", "Supabase", "Render", "GitHub", "Factory3 skills"],
                "outcomes": ["Live Freelance Center dashboard", "Reusable freelance_growth skills", "Supabase-backed jobs/proposals", "Portfolio generated from real Factory3 projects"],
                "portfolio_value": "Very high: it demonstrates a business automation product built to sell and operate freelance acquisition.",
                "asset_recommendations": ["1 screenshot of Home", "1 screenshot of Jobs analysis", "1 screenshot of generated proposal", "1 short video showing job-to-proposal flow"],
            })
        return candidates

    def _represented_companies(self, existing: set[str]) -> set[str]:
        represented = set()
        mapping = {
            "estoiko": "EMP_ESTOIKOLAB",
            "rstate": "EMP_CAMP_RSTATE",
            "rh1": "EMP_RH1",
            "logplat": "EMP_LOGPLAT",
        }
        for project_id in existing:
            text = str(project_id).lower()
            for key, company in mapping.items():
                if key in text:
                    represented.add(company)
        return represented

    def _recommendations(self, candidates: list[dict], dashboards: list[dict], verticals: list[dict]) -> list[str]:
        recs = []
        if candidates:
            recs.append(f"Agregar {len(candidates)} proyecto(s) detectado(s) al portafolio, empezando por los de mayor valor comercial.")
        recs.append("Grabar videos cortos de 45-90 segundos para los proyectos con dashboard vivo.")
        recs.append("Tomar screenshots con datos sensibles ocultos: overview, flujo principal y resultado final.")
        recs.append("Mantener un job diario a las 23:00 para auditar nuevas empresas/dashboards y generar pendientes.")
        if any(d["company_id"] == "EMP_FREELANCE_GROWTH" for d in dashboards):
            recs.append("Documentar Freelance Center como proyecto propio: es evidencia directa de sistema de ventas automatizado.")
        return recs

    def _dashboard_signals(self, app: Path) -> list[str]:
        text = app.read_text(encoding="utf-8", errors="replace").lower()
        signals = []
        for key in ["streamlit", "supabase", "render", "telegram", "meta", "landing", "jobs", "proposals", "leads", "campaign", "portfolio", "upload", "kpi", "pagos", "gastos", "cxc"]:
            if key in text:
                signals.append(key)
        return signals

    def _company_from_path(self, app: Path) -> str:
        parts = list(app.parts)
        for part in reversed(parts):
            if part.startswith("EMP_"):
                return part
        return app.parent.parent.name

    def _project_id(self, company: str, path: str) -> str:
        base = company.lower().replace("emp_", "")
        return re.sub(r"[^a-z0-9]+", "_", base).strip("_") + "_dashboard"

    def _title(self, company: str, dash: dict) -> str:
        if company == "EMP_FREELANCE_GROWTH":
            return "Freelance Center Dashboard"
        return f"{company} Dashboard System"

    def _type_from_signals(self, signals: list[str]) -> str:
        if "jobs" in signals or "proposals" in signals or "portfolio" in signals:
            return "freelance sales operations dashboard"
        if "campaign" in signals or "landing" in signals:
            return "campaign operations dashboard"
        if "leads" in signals:
            return "lead capture and operations dashboard"
        if "pagos" in signals or "gastos" in signals or "cxc" in signals:
            return "business operations dashboard"
        return "business dashboard"

    def _problem_from_company(self, company: str, signals: list[str]) -> str:
        if company == "EMP_FREELANCE_GROWTH":
            return "A freelancer needs to manage profile assets, portfolio evidence, job scoring and proposal generation from one place."
        return "The business needed a clearer operating view and repeatable workflow instead of scattered manual tracking."

    def _solution_from_signals(self, company: str, signals: list[str]) -> str:
        return f"Built a Streamlit dashboard for {company} connected to Factory3 skills and structured project data."

    def _stack_from_signals(self, signals: list[str]) -> list[str]:
        stack = ["Python", "Streamlit"]
        if "supabase" in signals:
            stack.append("Supabase")
        if "render" in signals:
            stack.append("Render")
        if "telegram" in signals:
            stack.append("Telegram")
        if "meta" in signals:
            stack.append("Meta APIs")
        stack.append("Factory3 skills")
        return list(dict.fromkeys(stack))

    def _outcomes_from_signals(self, signals: list[str]) -> list[str]:
        outcomes = ["Operational dashboard", "Reusable Factory3 workflow"]
        if "jobs" in signals:
            outcomes.append("Job analysis workflow")
        if "proposals" in signals:
            outcomes.append("Proposal generation workflow")
        if "leads" in signals:
            outcomes.append("Lead visibility")
        if "upload" in signals:
            outcomes.append("Asset upload workflow")
        if "kpi" in signals:
            outcomes.append("KPI visibility")
        return outcomes

    def _portfolio_value(self, company: str, signals: list[str]) -> str:
        if company == "EMP_FREELANCE_GROWTH":
            return "High: directly supports client acquisition and shows an end-to-end business tool."
        if "leads" in signals or "campaign" in signals:
            return "High: maps to common Upwork demand for lead capture and campaign operations."
        return "Medium: useful proof of business dashboard delivery."

    def _assets_for(self, signals: list[str]) -> list[str]:
        assets = ["2 dashboard screenshots", "1 short video demo", "1 before/after workflow note"]
        if "jobs" in signals or "proposals" in signals:
            assets.append("Video: paste job -> score -> proposal")
        if "upload" in signals:
            assets.append("Screenshot of upload/media manager")
        if "kpi" in signals:
            assets.append("Screenshot of KPI cards")
        return assets

    def _markdown(self, data: dict) -> str:
        lines = ["# Factory3 Portfolio Audit", "", f"Audited at: {data['audited_at']}", ""]
        lines.append("## Candidates")
        for item in data["portfolio_candidates"]:
            lines.extend([
                f"### {item['name']}",
                f"- ID: `{item['id']}`",
                f"- Type: {item['type']}",
                f"- Value: {item['portfolio_value']}",
                f"- Evidence: {', '.join(x for x in item.get('evidence', []) if x)}",
                "- Assets:",
            ])
            lines.extend([f"  - {a}" for a in item.get("asset_recommendations", [])])
            lines.append("")
        lines.append("## Recommendations")
        lines.extend([f"- {r}" for r in data["recommendations"]])
        return "\n".join(lines) + "\n"

    def _rel(self, root: Path, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(root)).replace("\\", "/")
        except Exception:
            return str(path).replace("\\", "/")
