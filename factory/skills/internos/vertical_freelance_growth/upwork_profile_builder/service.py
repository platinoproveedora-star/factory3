from __future__ import annotations

import json
from pathlib import Path


class UpworkProfileBuilderService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("portfolio_root") or "companies/EMP_FREELANCE_GROWTH/portfolio")
        profile = self._read_json(root / "profile.json")
        projects = self._read_json(root / "projects.json").get("projects", [])
        if not profile:
            return {"ok": False, "error": f"profile.json no encontrado o invalido: {root / 'profile.json'}"}

        name = profile.get("name") or "AI Automation Builder"
        positioning = profile.get("positioning") or profile.get("headline") or "AI automation systems for business operations"
        services = profile.get("core_services") or profile.get("services") or []
        stack = profile.get("technical_stack") or profile.get("stack") or profile.get("tools") or []
        strongest_projects = projects[:4]

        title = "AI Automation Developer | Chat Agents, Lead Capture, Dashboards"
        title_es = "Desarrollador de Automatizacion IA | Agentes Chat, Leads y Dashboards"
        overview = self._overview(name, positioning, services, stack, strongest_projects)
        overview_es = self._overview_es(name, positioning, services, stack, strongest_projects)
        skills = self._skills(services, stack)
        output = {
            "title": title,
            "title_es": title_es,
            "overview": overview,
            "overview_es": overview_es,
            "skills": skills,
            "project_highlights": [
                f"{p.get('name')}: {p.get('solution')}" for p in strongest_projects if p.get("name")
            ],
            "project_highlights_es": [
                f"{p.get('name')}: {self._solution_es(p)}" for p in strongest_projects if p.get("name")
            ],
        }

        if context.get("save", True):
            out = root / "upwork" / "profile_draft.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(self._markdown(output), encoding="utf-8")
            output["saved_to"] = str(out)
        return {"ok": True, "data": output}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _overview(self, name: str, positioning: str, services: list, stack: list, projects: list) -> str:
        service_text = ", ".join(services[:5]) if services else "AI agents, dashboards and automation workflows"
        stack_text = ", ".join(stack[:8]) if stack else "Python, APIs, databases and cloud deployment"
        proof = "; ".join(p.get("name", "") for p in projects if p.get("name"))
        positioning = positioning.rstrip(".")
        return (
            f"I help companies turn repetitive sales, operations and customer conversations into working AI systems.\n\n"
            f"My focus is {positioning}. I build practical tools: {service_text}.\n\n"
            f"I work with {stack_text}, and I care about shipping systems that are easy to test, explain and improve.\n\n"
            f"Recent work includes {proof}. These are not just demos: they are structured as reusable Factory3 modules with dashboards, storage and business workflows.\n\n"
            f"If you need someone who can understand the business process, design the automation and build the first working version fast, I can help."
        )

    def _overview_es(self, name: str, positioning: str, services: list, stack: list, projects: list) -> str:
        service_text = ", ".join(services[:5]) if services else "agentes IA, dashboards y automatizaciones operativas"
        stack_text = ", ".join(stack[:8]) if stack else "Python, APIs, bases de datos y despliegue en la nube"
        proof = "; ".join(p.get("name", "") for p in projects if p.get("name"))
        return (
            "Ayudo a empresas a convertir conversaciones, ventas y procesos repetitivos en sistemas de IA que funcionan en la operacion real.\n\n"
            f"Mi enfoque es construir automatizaciones practicas: {service_text}.\n\n"
            f"Trabajo con {stack_text}. Me enfoco en entregar herramientas claras, probables y faciles de mejorar.\n\n"
            f"Proyectos recientes: {proof}. No son solo demos: estan organizados como modulos reutilizables de Factory3 con dashboards, almacenamiento y flujos de negocio.\n\n"
            "Si necesitas a alguien que entienda el proceso del negocio, disene la automatizacion y construya una primera version funcional rapido, puedo ayudarte."
        )

    def _solution_es(self, project: dict) -> str:
        solution = str(project.get("solution") or "")
        replacements = {
            "Built": "Construido",
            "Activated": "Activado",
            "a Telegram-based AI agent system": "un sistema de agentes IA en Telegram",
            "a configurable landing page": "una landing page configurable",
            "a Factory3-based operations system": "un sistema operativo basado en Factory3",
        }
        for old, new in replacements.items():
            solution = solution.replace(old, new)
        return solution or "Sistema construido para resolver un flujo operativo real."

    def _skills(self, services: list, stack: list) -> list[str]:
        base = [
            "AI Chatbot Development",
            "Business Process Automation",
            "Lead Generation Automation",
            "Python",
            "API Integration",
            "Dashboard Development",
            "Supabase",
            "Streamlit",
            "Telegram Bots",
            "Prompt Engineering",
        ]
        merged = base + [str(x) for x in services + stack]
        return list(dict.fromkeys([x for x in merged if x]))[:15]

    def _markdown(self, output: dict) -> str:
        skills = "\n".join(f"- {s}" for s in output["skills"])
        highlights = "\n".join(f"- {h}" for h in output["project_highlights"])
        highlights_es = "\n".join(f"- {h}" for h in output["project_highlights_es"])
        return (
            f"# English Version\n\n"
            f"## {output['title']}\n\n"
            f"### Overview\n{output['overview']}\n\n"
            f"### Skills\n{skills}\n\n"
            f"### Project Highlights\n{highlights}\n\n"
            f"---\n\n"
            f"# Version en Espanol\n\n"
            f"## {output['title_es']}\n\n"
            f"### Resumen\n{output['overview_es']}\n\n"
            f"### Habilidades\n{skills}\n\n"
            f"### Proyectos Destacados\n{highlights_es}\n"
        )
