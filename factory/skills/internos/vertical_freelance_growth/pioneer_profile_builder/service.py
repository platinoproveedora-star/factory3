"""Pioneer profile builder — genera respuestas para la aplicacion Pioneer (YC Fellowship)."""
from __future__ import annotations

import json
from pathlib import Path


class PioneerProfileBuilderService:

    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("portfolio_root") or "companies/EMP_FREELANCE_GROWTH/portfolio")
        profile = self._read_json(root / "profile.json")
        projects = self._read_json(root / "projects.json").get("projects", [])

        if not profile:
            return {"ok": False, "error": f"profile.json no encontrado: {root / 'profile.json'}"}

        output = self._build(profile, projects)

        if context.get("save", True):
            out = root / "pioneer" / "profile_draft.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(self._markdown(output), encoding="utf-8")
            output["saved_to"] = str(out)

        return {"ok": True, "data": output}

    # ── core builder ──────────────────────────────────────────────────────────

    def _build(self, profile: dict, projects: list) -> dict:
        name        = profile.get("name", "Alfie Correa")
        positioning = profile.get("positioning", "")
        services    = profile.get("core_services", [])
        stack       = profile.get("technical_stack", [])
        proofs      = profile.get("proof_points", [])
        pricing     = profile.get("pricing_notes", {})
        targets     = profile.get("target_clients", [])

        # Pick best project (first = Estoiko Lab, second best = LOGPLAT — real prod)
        top_project   = projects[0] if projects else {}
        prod_projects = [p for p in projects if "real production" in " ".join(p.get("outcomes", [])).lower()]
        prod_project  = prod_projects[0] if prod_projects else (projects[1] if len(projects) > 1 else top_project)

        return {
            "name":          name,
            "what_building": self._what_building(positioning, services, proofs),
            "why_now":       self._why_now(services, targets),
            "traction":      self._traction(proofs, prod_project, projects),
            "background":    self._background(name, stack, projects),
            "goals":         self._goals(pricing, targets),
            "top_project":   self._project_summary(top_project),
            "prod_project":  self._project_summary(prod_project),
        }

    def _what_building(self, positioning: str, services: list, proofs: list) -> str:
        s1 = services[0] if services else "AI chat agents for business operations"
        s2 = services[1] if len(services) > 1 else "lead capture and qualification systems"
        return (
            "I am building Factory3: a modular runtime that lets any business deploy AI-powered chat agents, "
            "lead capture flows, operations dashboards and campaign automations — without starting from scratch each time.\n\n"
            f"The core insight is that most small business automation projects share the same structure: a company config, "
            f"an AI prompt layer, a data model, and a way to expose it via bot or dashboard. "
            f"Factory3 abstracts that into skills, bots and company modules that can be composed and deployed on Render in hours, not weeks.\n\n"
            f"Right now Factory3 powers {len(proofs)} live client systems: a freight logistics operation, "
            f"a marketing agency chat agent, a recruiting dashboard and a real estate campaign system. "
            f"The next milestone is turning Factory3 into a service I can offer on Upwork and through Estoiko Lab — "
            f"an agency partner who sells AI chat agents to her clients using my stack."
        )

    def _why_now(self, services: list, targets: list) -> str:
        client_types = ", ".join(targets[:3]) if targets else "marketing agencies, local businesses, recruiting teams"
        return (
            "Small businesses know they need AI but do not know where to start. "
            "Most AI tools either require technical teams or are too generic to fit real operations. "
            "There is a clear gap for someone who can take a business process — a sales conversation, a trip log, a job vacancy — "
            "and turn it into a working automated system in a week.\n\n"
            f"The clients who need this most are {client_types}. "
            "They do not need a SaaS subscription; they need one person who understands their workflow and ships something they can actually use. "
            "Factory3 is built exactly for that: composable, deployable, and easy to explain to a non-technical client."
        )

    def _traction(self, proofs: list, prod_project: dict, projects: list) -> str:
        proof_lines = "\n".join(f"- {p}" for p in proofs) if proofs else ""
        prod_name   = prod_project.get("name", "")
        prod_out    = ", ".join(prod_project.get("outcomes", [])[:3]) if prod_project else ""
        n = len(projects)
        return (
            f"Factory3 currently has {n} active company modules, each with its own Supabase schema, skills and bot or dashboard:\n\n"
            f"{proof_lines}\n\n"
            f"The strongest proof of traction is {prod_name}: {prod_out}. "
            "This is not a demo — it is used daily by an operations team to capture freight trips, expenses and payments. "
            "The dashboard replaced their spreadsheet dependency.\n\n"
            "On the commercial side, Estoiko Lab (a marketing agency partner) is now selling AI chat agents to clients using my stack. "
            "The first agent is live on Telegram. Lead capture and conversation orchestration are working end to end."
        )

    def _background(self, name: str, stack: list, projects: list) -> str:
        stack_text = ", ".join(stack[:6]) if stack else "Python, FastAPI, Supabase, Streamlit, Render, Telegram"
        n = len(projects)
        return (
            f"I am {name}, a developer based in Mexico focused on AI automation for business operations.\n\n"
            f"My background is in building practical systems: {stack_text}. "
            "I started Factory3 as a personal project to systematize how I build client work — "
            "instead of building each project from scratch, I create reusable skills and company modules that compose into full systems.\n\n"
            f"I have built {n} complete systems in the last few months, all deployed on Render, connected to Supabase and integrated with Telegram bots or Streamlit dashboards. "
            "I work alone, moving fast and building things that real users can operate the same week I ship them."
        )

    def _goals(self, pricing: dict, targets: list) -> str:
        hourly = pricing.get("starter_hourly_usd", 25)
        model  = pricing.get("preferred_model", "fixed-scope packages for MVPs, dashboards and agent demos")
        return (
            "In the next 6 months I want to:\n\n"
            f"1. Reach $3,000–$5,000/month from freelance work on Upwork, targeting {', '.join(targets[:2]) if targets else 'marketing agencies and local businesses'}.\n"
            "2. Build 3+ verified case studies with screenshots and measurable outcomes to anchor my profile.\n"
            "3. Turn Factory3 into a product that Estoiko Lab can sell to 5 paying clients — proving the model works at scale.\n"
            "4. Document the Factory3 pattern well enough that I can onboard a second developer to help with delivery.\n\n"
            f"My starting rate is ${hourly}/hr, with a preference for {model}. "
            "The goal is not just revenue — it is to prove that a solo developer in LATAM can build production-grade AI systems and charge for them."
        )

    def _project_summary(self, project: dict) -> str:
        if not project:
            return ""
        outcomes = "; ".join(project.get("outcomes", [])[:3])
        return (
            f"{project.get('name', '')}: {project.get('problem', '')} — "
            f"{project.get('solution', '')} Results: {outcomes}."
        )

    # ── markdown renderer ─────────────────────────────────────────────────────

    def _markdown(self, o: dict) -> str:
        return f"""# Pioneer Profile — {o['name']}

## What are you building?

{o['what_building']}

## Why now?

{o['why_now']}

## What traction do you have?

{o['traction']}

## Tell us about yourself

{o['background']}

## What are your goals?

{o['goals']}

---

## Top Project (for portfolio)
{o['top_project']}

## Production Project (strongest proof)
{o['prod_project']}
"""

    # ── util ──────────────────────────────────────────────────────────────────

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
