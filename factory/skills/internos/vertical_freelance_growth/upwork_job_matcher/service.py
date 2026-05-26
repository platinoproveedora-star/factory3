from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


class UpworkJobMatcherService:
    def ejecutar(self, context: dict) -> dict:
        job = (context.get("job_description") or context.get("job") or "").strip()
        if not job:
            return {"ok": False, "error": "job_description requerido"}

        root = Path(context.get("portfolio_root") or "companies/EMP_FREELANCE_GROWTH/portfolio")
        profile = self._read_json(root / "profile.json")
        projects = self._read_json(root / "projects.json").get("projects", [])

        analysis = self._analyze(job, profile, projects)
        if context.get("save", True):
            out_dir = root / "upwork" / "jobs"
            out_dir.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", job.lower())[:45].strip("-") or "job"
            out = out_dir / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{slug}.json"
            out.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
            analysis["saved_to"] = str(out)
        return {"ok": True, "data": analysis}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _tokens(self, text: str) -> set[str]:
        stop = {"and", "the", "for", "with", "that", "this", "from", "need", "want", "you", "your", "are", "can", "our", "una", "para", "con", "que", "del", "los", "las"}
        return {w.lower() for w in re.findall(r"[a-zA-Z0-9_]+", text) if len(w) > 3 and w.lower() not in stop}

    def _analyze(self, job: str, profile: dict, projects: list[dict]) -> dict:
        job_l = job.lower()
        profile_text = json.dumps(profile, ensure_ascii=False).lower()
        project_texts = [(p, json.dumps(p, ensure_ascii=False).lower()) for p in projects]
        tokens = self._tokens(job)

        service_hits = self._hits(tokens, profile_text)
        project_scores = []
        for project, text in project_texts:
            score = self._hits(tokens, text)
            if score:
                project_scores.append({"id": project.get("id"), "name": project.get("name"), "score": score, "type": project.get("type")})
        project_scores.sort(key=lambda row: row["score"], reverse=True)

        positive_terms = {
            "chatbot": 12, "chat": 8, "ai": 8, "automation": 12, "dashboard": 12, "lead": 12,
            "supabase": 10, "streamlit": 10, "python": 10, "telegram": 8, "whatsapp": 8,
            "api": 8, "crm": 6, "landing": 6, "business": 4, "workflow": 10,
        }
        negative_terms = {
            "blockchain": -18, "crypto": -18, "nft": -20, "game": -12, "mobile app": -12,
            "ios": -10, "android": -10, "shopify": -8, "wordpress plugin": -8,
            "scrape upwork": -25, "guaranteed": -10, "cheap": -8,
        }

        score = 35 + min(service_hits * 3, 20) + min(sum(p["score"] for p in project_scores[:3]) * 2, 25)
        matched_terms = []
        risk_terms = []
        for term, points in positive_terms.items():
            if term in job_l:
                score += points
                matched_terms.append(term)
        for term, points in negative_terms.items():
            if term in job_l:
                score += points
                risk_terms.append(term)
        if len(job) < 250:
            score -= 8
            risk_terms.append("descripcion corta/poco clara")
        score = max(0, min(100, score))

        if score >= 78:
            decision = "apply_now"
            decision_es = "Aplicar ahora"
        elif score >= 58:
            decision = "apply_if_budget_ok"
            decision_es = "Aplicar si presupuesto y cliente se ven bien"
        else:
            decision = "skip_or_low_priority"
            decision_es = "No aplicar o dejar baja prioridad"

        strengths = self._strengths(matched_terms, project_scores)
        risks = self._risks(risk_terms, job_l)
        angle = self._angle(matched_terms, project_scores)

        return {
            "score": score,
            "decision": decision,
            "decision_es": decision_es,
            "matched_terms": matched_terms,
            "risk_terms": risk_terms,
            "relevant_projects": project_scores[:3],
            "strengths": strengths,
            "risks": risks,
            "proposal_angle": angle,
            "next_step": "Si score >= 58, usar upwork_proposal_generator con esta vacante.",
        }

    def _hits(self, tokens: set[str], text: str) -> int:
        return sum(1 for token in tokens if token in text)

    def _strengths(self, matched_terms: list[str], projects: list[dict]) -> list[str]:
        strengths = []
        if matched_terms:
            strengths.append("La vacante toca capacidades que ya estan en el portafolio: " + ", ".join(matched_terms[:8]) + ".")
        if projects:
            strengths.append("Hay proyectos reales que se pueden usar como prueba: " + ", ".join(p["name"] for p in projects[:3]) + ".")
        strengths.append("Se puede proponer un MVP claro con alcance corto: flujo, captura de datos, dashboard y deploy.")
        return strengths

    def _risks(self, risk_terms: list[str], job_l: str) -> list[str]:
        risks = []
        if risk_terms:
            risks.append("Revisar estos focos antes de aplicar: " + ", ".join(risk_terms) + ".")
        if "budget" not in job_l and "$" not in job_l:
            risks.append("No se detecto presupuesto claro; conviene validar alcance y pago antes de invertir mucho tiempo.")
        if "urgent" in job_l or "asap" in job_l:
            risks.append("Cliente con urgencia: proponer milestone inicial pequeno para evitar scope creep.")
        return risks or ["No hay riesgos fuertes detectados con reglas actuales."]

    def _angle(self, matched_terms: list[str], projects: list[dict]) -> str:
        if any(term in matched_terms for term in ["chatbot", "chat", "telegram", "whatsapp"]):
            return "Abrir con experiencia construyendo agentes conversacionales que capturan leads y guardan datos en dashboard."
        if any(term in matched_terms for term in ["dashboard", "supabase", "streamlit"]):
            return "Abrir con experiencia creando dashboards operativos conectados a Supabase y flujos reales de negocio."
        if projects:
            return f"Abrir con el caso mas parecido: {projects[0]['name']}, explicando problema, solucion y resultado."
        return "Abrir con una propuesta de MVP corto: entender proceso, construir version funcional, probar con datos reales."
