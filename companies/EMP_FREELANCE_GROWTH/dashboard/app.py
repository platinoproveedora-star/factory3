"""Freelance Center dashboard for EMP_FREELANCE_GROWTH."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[3]
COMPANY_DIR = ROOT / "companies" / "EMP_FREELANCE_GROWTH"
PORTFOLIO_DIR = COMPANY_DIR / "portfolio"
UPWORK_DIR = PORTFOLIO_DIR / "upwork"
CLIENTS_DIR = COMPANY_DIR / "clients"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENV_PATH = ROOT / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from factory.engine.skill_loader import SkillLoader
from factory.engine.skill_runner import SkillRunner
from companies.EMP_FREELANCE_GROWTH.dashboard import db


st.set_page_config(
    page_title="Freelance Center",
    page_icon="FC",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --page: #f6f7f9;
        --surface: #ffffff;
        --ink: #172033;
        --muted: #667085;
        --line: #d9dee8;
        --accent: #176f6b;
        --accent-2: #b66a2c;
        --soft: #eef4f3;
      }
      [data-testid="stAppViewContainer"] { background: var(--page); }
      [data-testid="stHeader"] { background: rgba(246,247,249,.92); }
      [data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #263244;
      }
      [data-testid="stSidebar"] * { color: #eef2f7 !important; }
      .main .block-container { padding-top: 1.35rem; max-width: 1280px; }
      h1, h2, h3, h4, p, li, label, span { color: var(--ink); letter-spacing: 0; }
      [data-testid="stCaptionContainer"] p { color: var(--muted); }
      input, textarea, [role="combobox"] {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
        background: #fff !important;
      }
      textarea { border: 1px solid var(--line) !important; }
      .fc-hero {
        background: linear-gradient(135deg, #ffffff 0%, #eef4f3 100%);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 22px 24px;
        margin-bottom: 18px;
      }
      .fc-hero small {
        display: block;
        color: var(--accent);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .08em;
        margin-bottom: 8px;
      }
      .fc-hero h1 {
        margin: 0 0 8px 0;
        font-size: 34px;
        line-height: 1.1;
      }
      .fc-hero p {
        max-width: 850px;
        margin: 0;
        color: var(--muted);
        font-size: 15px;
      }
      .fc-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 14px 0 20px;
      }
      .fc-stat {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px;
        min-height: 92px;
      }
      .fc-stat span { display: block; color: var(--muted); font-size: 12px; margin-bottom: 10px; }
      .fc-stat strong { display: block; color: var(--ink); font-size: 24px; line-height: 1.1; }
      .fc-panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
      }
      .fc-panel h3 { margin: 0 0 8px 0; font-size: 17px; }
      .fc-panel p { color: var(--muted); margin: 0 0 10px 0; }
      .fc-chip {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 999px;
        background: var(--soft);
        color: var(--accent);
        border: 1px solid #c9ddda;
        margin: 0 6px 6px 0;
        font-size: 12px;
        font-weight: 650;
      }
      .fc-row {
        border-top: 1px solid var(--line);
        padding: 12px 0;
      }
      .fc-row:first-child { border-top: 0; padding-top: 0; }
      .fc-muted { color: var(--muted); font-size: 13px; }
      .stButton button {
        border-radius: 8px;
        border: 1px solid #b8c4d6;
        background: #fff;
        color: var(--ink);
      }
      .stButton button[kind="primary"] {
        background: var(--accent);
        color: white;
        border-color: var(--accent);
      }
      code, pre, [data-testid="stCodeBlock"] pre {
        color: var(--ink);
        background: #fbfcfe;
        border: 1px solid var(--line);
        border-radius: 8px;
      }
      @media (max-width: 900px) {
        .fc-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .fc-hero h1 { font-size: 28px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _runner() -> SkillRunner:
    return SkillRunner(SkillLoader(ROOT / "factory" / "skills" / "internos"))


def _run_skill(name: str, context: dict) -> dict:
    return _runner().run(name, context, source="internos")


def _portfolio_context() -> dict:
    return {"portfolio_root": str(PORTFOLIO_DIR), "save": True}


def _job_files() -> list[Path]:
    folder = UPWORK_DIR / "jobs"
    return sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if folder.exists() else []


def _proposal_files() -> list[Path]:
    folder = UPWORK_DIR / "proposals"
    return sorted([p for p in folder.glob("*.md") if p.name != ".gitkeep"], key=lambda p: p.stat().st_mtime, reverse=True) if folder.exists() else []


def _supabase_jobs() -> list[dict]:
    return db.select(
        "jobs",
        {
            "select": "id,job_text,score,decision,decision_es,matched_terms,risk_terms,relevant_projects,strengths,risks,proposal_angle,status,created_at",
            "order": "created_at.desc",
            "limit": "100",
        },
    )


def _supabase_proposals() -> list[dict]:
    return db.select(
        "proposals",
        {
            "select": "id,job_text,proposal_text,matched_projects,status,created_at",
            "order": "created_at.desc",
            "limit": "100",
        },
    )


def _save_job_to_supabase(job_text: str, analysis: dict) -> dict | None:
    return db.insert(
        "jobs",
        {
            "company_id": "EMP_FREELANCE_GROWTH",
            "source": "upwork",
            "job_text": job_text,
            "score": analysis.get("score"),
            "decision": analysis.get("decision"),
            "decision_es": analysis.get("decision_es"),
            "matched_terms": analysis.get("matched_terms") or [],
            "risk_terms": analysis.get("risk_terms") or [],
            "relevant_projects": analysis.get("relevant_projects") or [],
            "strengths": analysis.get("strengths") or [],
            "risks": analysis.get("risks") or [],
            "proposal_angle": analysis.get("proposal_angle"),
            "saved_file": analysis.get("saved_to"),
            "status": "analyzed",
        },
    )


def _save_proposal_to_supabase(job_text: str, data: dict) -> dict | None:
    return db.insert(
        "proposals",
        {
            "company_id": "EMP_FREELANCE_GROWTH",
            "source": "upwork",
            "job_text": job_text,
            "proposal_text": data.get("proposal") or "",
            "matched_projects": data.get("matched_projects") or [],
            "saved_file": data.get("saved_to"),
            "status": "draft",
        },
    )


def _render_hero() -> None:
    st.markdown(
        """
        <div class="fc-hero">
          <small>EMP_FREELANCE_GROWTH</small>
          <h1>Freelance Center</h1>
          <p>Centro operativo para convertir proyectos reales de Factory3 en perfil, portafolio, vacantes evaluadas y propuestas listas para vender.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _stat(label: str, value: str) -> str:
    return f'<div class="fc-stat"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'


def _home() -> None:
    profile = _read_json(PORTFOLIO_DIR / "profile.json")
    projects = _read_json(PORTFOLIO_DIR / "projects.json").get("projects", [])
    jobs_count = len(_supabase_jobs()) if db.configured() else len(_job_files())
    proposals_count = len(_supabase_proposals()) if db.configured() else len(_proposal_files())

    st.markdown(
        '<div class="fc-grid">'
        + _stat("Perfil", "Listo" if (UPWORK_DIR / "profile_draft.md").exists() else "Pendiente")
        + _stat("Proyectos", str(len(projects)))
        + _stat("Jobs Analizados", str(jobs_count))
        + _stat("Propuestas", str(proposals_count))
        + "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 0.95])
    with left:
        st.markdown('<div class="fc-panel"><h3>Prioridad de hoy</h3><p>Dejar el registro de Upwork listo con copy, portafolio y primeros assets.</p></div>', unsafe_allow_html=True)
        checklist = [
            ("Perfil bilingue generado", (UPWORK_DIR / "profile_draft.md").exists()),
            ("Case studies generados", (UPWORK_DIR / "case_studies.md").exists()),
            ("Portfolio pack generado", (UPWORK_DIR / "portfolio_pack.md").exists()),
            ("Agregar screenshots limpios", False),
            ("Crear cuenta / completar registro Upwork", False),
        ]
        for label, done in checklist:
            st.checkbox(label, value=done, disabled=True)
    with right:
        st.markdown('<div class="fc-panel"><h3>Posicionamiento</h3>', unsafe_allow_html=True)
        st.write(profile.get("positioning", ""))
        st.markdown("</div>", unsafe_allow_html=True)
        services = profile.get("core_services", [])
        st.markdown('<div class="fc-panel"><h3>Servicios vendibles</h3>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="fc-chip">{escape(s)}</span>' for s in services), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="fc-panel"><h3>Storage</h3>', unsafe_allow_html=True)
        st.write("Supabase conectado" if db.configured() else "Modo archivos locales")
        if db.last_error():
            st.caption(db.last_error())
        st.markdown("</div>", unsafe_allow_html=True)


def _profile() -> None:
    st.subheader("Profile Builder")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Regenerar perfil Upwork", type="primary"):
            result = _run_skill("vertical_freelance_growth/upwork_profile_builder", _portfolio_context())
            if result.get("ok"):
                st.success("Perfil regenerado.")
            else:
                st.error(result.get("error", "Error desconocido"))
        st.caption("Genera ingles + espanol desde profile.json y projects.json.")
    with col2:
        if st.button("Regenerar case studies"):
            result = _run_skill("vertical_freelance_growth/upwork_case_study_generator", _portfolio_context())
            if result.get("ok"):
                st.success("Case studies regenerados.")
            else:
                st.error(result.get("error", "Error desconocido"))

    st.markdown("### Draft actual")
    text = _read_text(UPWORK_DIR / "profile_draft.md")
    st.text_area("profile_draft.md", value=text, height=520)


def _portfolio() -> None:
    st.subheader("Portfolio")
    if st.button("Regenerar portfolio pack", type="primary"):
        result = _run_skill("vertical_freelance_growth/upwork_portfolio_pack_builder", _portfolio_context())
        if result.get("ok"):
            st.success("Portfolio pack regenerado.")
        else:
            st.error(result.get("error", "Error desconocido"))

    projects = _read_json(PORTFOLIO_DIR / "projects.json").get("projects", [])
    for project in projects:
        st.markdown('<div class="fc-panel">', unsafe_allow_html=True)
        st.markdown(f"### {project.get('name', 'Proyecto')}")
        st.caption(project.get("type", ""))
        st.write(project.get("problem", ""))
        st.write(project.get("solution", ""))
        st.markdown("".join(f'<span class="fc-chip">{escape(str(s))}</span>' for s in project.get("stack", [])), unsafe_allow_html=True)
        with st.expander("Resultados y assets faltantes"):
            st.markdown("**Resultados**")
            for item in project.get("outcomes", []):
                st.write(f"- {item}")
            st.markdown("**Assets recomendados**")
            st.write("- Screenshot dashboard / flujo principal")
            st.write("- Screenshot con datos sensibles ocultos")
            st.write("- Video corto demo si aplica")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Portfolio pack generado")
    st.text_area("portfolio_pack.md", value=_read_text(UPWORK_DIR / "portfolio_pack.md"), height=420)


def _jobs() -> None:
    st.subheader("Jobs")
    if "job_text_input" not in st.session_state:
        st.session_state["job_text_input"] = ""
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Limpiar vacante"):
            st.session_state["job_text_input"] = ""
            st.rerun()
    with c2:
        st.caption("Pega una vacante nueva y analiza si conviene aplicar.")
    job = st.text_area(
        "Pega aqui la vacante de Upwork",
        key="job_text_input",
        height=240,
        placeholder="Job title, description, budget, requirements...",
    )
    if st.button("Analizar vacante", type="primary", disabled=not job.strip()):
        result = _run_skill("vertical_freelance_growth/upwork_job_matcher", {**_portfolio_context(), "job_description": job})
        if result.get("ok"):
            data = result.get("data", {})
            if db.configured():
                saved = _save_job_to_supabase(job, data)
                if saved:
                    data["supabase_id"] = saved.get("id")
                elif db.last_error():
                    st.warning(f"No se guardo en Supabase: {db.last_error()}")
            st.success(f"Score {data.get('score')} - {data.get('decision_es')}")
            st.json(data)
        else:
            st.error(result.get("error", "Error desconocido"))

    st.markdown("### Historial")
    if db.configured():
        rows = _supabase_jobs()
        if not rows:
            st.info("Todavia no hay vacantes en Supabase.")
            if db.last_error():
                st.caption(db.last_error())
        for row in rows[:20]:
            with st.expander(f"{row.get('created_at', '')} | score {row.get('score', 'n/a')} | {row.get('decision_es', '')}"):
                st.json(row)
    else:
        files = _job_files()
        if not files:
            st.info("Todavia no hay vacantes analizadas.")
        for path in files[:20]:
            data = _read_json(path)
            with st.expander(f"{path.stem} | score {data.get('score', 'n/a')} | {data.get('decision_es', '')}"):
                st.json(data)


def _proposals() -> None:
    st.subheader("Proposals")
    job = st.text_area("Vacante para generar propuesta", height=220)
    if st.button("Generar propuesta", type="primary", disabled=not job.strip()):
        result = _run_skill("vertical_freelance_growth/upwork_proposal_generator", {**_portfolio_context(), "job_description": job})
        if result.get("ok"):
            data = result.get("data", {})
            if db.configured():
                saved = _save_proposal_to_supabase(job, data)
                if saved:
                    data["supabase_id"] = saved.get("id")
                elif db.last_error():
                    st.warning(f"No se guardo en Supabase: {db.last_error()}")
            st.success(f"Propuesta guardada: {data.get('saved_to')}")
            st.text_area("Propuesta", value=data.get("proposal", ""), height=420)
        else:
            st.error(result.get("error", "Error desconocido"))

    st.markdown("### Propuestas guardadas")
    if db.configured():
        rows = _supabase_proposals()
        if not rows:
            st.info("Todavia no hay propuestas en Supabase.")
            if db.last_error():
                st.caption(db.last_error())
        for row in rows[:20]:
            with st.expander(f"{row.get('created_at', '')} | {row.get('status', '')}"):
                st.text_area(str(row.get("id")), value=row.get("proposal_text", ""), height=320)
                st.json({"matched_projects": row.get("matched_projects"), "job_text": row.get("job_text")})
    else:
        files = _proposal_files()
        if not files:
            st.info("Todavia no hay propuestas generadas.")
        for path in files[:20]:
            with st.expander(path.name):
                st.text_area(str(path), value=_read_text(path), height=320)


def _clients() -> None:
    st.subheader("Clients")
    st.caption("Orquesta alta de cliente, proyecto, entregables y repo opcional desde una vacante ganada o brief.")

    uploaded = st.file_uploader("Subir brief del cliente", type=["txt", "md"])
    uploaded_text = ""
    if uploaded is not None:
        uploaded_text = uploaded.getvalue().decode("utf-8", errors="replace")

    if "client_brief_input" not in st.session_state:
        st.session_state["client_brief_input"] = uploaded_text
    elif uploaded_text:
        st.session_state["client_brief_input"] = uploaded_text

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("Limpiar brief"):
            st.session_state["client_brief_input"] = ""
            st.rerun()
    with c2:
        dry_run = st.checkbox("Dry run", value=False)
    with c3:
        create_repo = st.checkbox("Crear repo GitHub privado", value=False)

    brief = st.text_area(
        "Brief / vacante ganada / notas del cliente",
        key="client_brief_input",
        height=220,
        placeholder="Cliente, objetivo, alcance, presupuesto, deadline, entregables...",
    )

    col1, col2 = st.columns(2)
    with col1:
        client_name = st.text_input("Nombre del cliente", placeholder="Cliente Upwork")
        platform = st.selectbox("Origen", ["upwork", "pioneer", "direct", "referral"])
    with col2:
        budget = st.text_input("Presupuesto", placeholder="$500")
        deadline = st.text_input("Deadline", placeholder="2 semanas")

    project_name = st.text_input("Nombre del proyecto", placeholder="AI chatbot / dashboard / automation")

    if st.button("Orquestar cliente", type="primary", disabled=not brief.strip()):
        result = _run_skill("vertical_upwork_clients/upwork_client_orchestrator", {
            "clients_root": str(CLIENTS_DIR),
            "brief": brief,
            "client_name": client_name.strip(),
            "project_name": project_name.strip(),
            "platform": platform,
            "budget": budget.strip(),
            "deadline": deadline.strip(),
            "create_repo": create_repo,
            "repo_private": True,
            "dry_run": dry_run,
        })
        if result.get("ok"):
            data = result.get("data", {})
            client = data.get("client", {})
            project = data.get("project", {})
            st.success(f"Cliente preparado: {client.get('client_id')} | {project.get('project_name')}")
            st.json(data)
        else:
            st.error(result.get("error", "Error desconocido"))

    st.markdown("### Registro de clientes")
    status = _run_skill("vertical_upwork_clients/upwork_client_status", {"clients_root": str(CLIENTS_DIR)})
    if not status.get("ok"):
        st.error(status.get("error", "No se pudo leer el registro."))
        return

    rows = (status.get("data") or {}).get("clients", [])
    if not rows:
        st.info("Todavia no hay clientes registrados.")
        return

    st.dataframe(rows, use_container_width=True)
    for row in rows:
        client_id = row.get("client_id")
        with st.expander(f"{client_id} | {row.get('client_name', '')} | {row.get('project_status', '')}"):
            client_dir = CLIENTS_DIR / str(client_id)
            st.markdown("**client.json**")
            st.json(_read_json(client_dir / "client.json"))
            st.markdown("**project.json**")
            st.json(_read_json(client_dir / "project.json"))
            st.markdown("**deliverables.md**")
            st.text_area(f"deliverables-{client_id}", value=_read_text(client_dir / "deliverables.md"), height=220)


def _checklist() -> None:
    st.subheader("Registration Checklist")
    checklist_path = UPWORK_DIR / "registration_checklist.md"
    default = """# Upwork Registration Checklist

- Definir titulo final.
- Copiar overview en ingles desde profile_draft.md.
- Seleccionar skills principales.
- Subir 3-4 proyectos de portfolio.
- Agregar screenshots limpios por proyecto.
- Definir tarifa inicial.
- Preparar primera propuesta de prueba.
"""
    current = _read_text(checklist_path) or default
    edited = st.text_area("Checklist editable", value=current, height=420)
    if st.button("Guardar checklist", type="primary"):
        _write_text(checklist_path, edited)
        st.success("Checklist guardado.")


def _audit() -> None:
    st.subheader("Factory3 Portfolio Audit")
    st.caption("Detecta empresas, dashboards y skills que pueden convertirse en proyectos vendibles.")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Auditar Factory3", type="primary"):
            result = _run_skill("vertical_freelance_growth/factory_portfolio_auditor", {**_portfolio_context(), "root": str(ROOT)})
            if result.get("ok"):
                st.success("Auditoria generada.")
                st.session_state["last_audit"] = result.get("data", {})
            else:
                st.error(result.get("error", "Error desconocido"))
    with c2:
        if st.button("Analizar gaps"):
            result = _run_skill("vertical_freelance_growth/portfolio_gap_analyzer", _portfolio_context())
            if result.get("ok"):
                st.success("Gaps generados.")
                st.session_state["last_gaps"] = result.get("data", {})
            else:
                st.error(result.get("error", "Error desconocido"))

    audit_data = st.session_state.get("last_audit") or _read_json(PORTFOLIO_DIR / "factory_audit.json")
    gaps_data = st.session_state.get("last_gaps") or {}

    if audit_data:
        companies = audit_data.get("companies", [])
        dashboards = audit_data.get("dashboards", [])
        verticals = audit_data.get("verticals", [])
        candidates = audit_data.get("portfolio_candidates", [])
        projects = _read_json(PORTFOLIO_DIR / "projects.json").get("projects", [])

        st.markdown(
            '<div class="fc-grid">'
            + _stat("Empresas Detectadas", str(len(companies)))
            + _stat("Dashboards", str(len(dashboards)))
            + _stat("Verticales", str(len(verticals)))
            + _stat("Candidatos Nuevos", str(len(candidates)))
            + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("### Resumen de Empresas")
        for company in companies:
            tags = []
            if company.get("has_dashboard"):
                tags.append("dashboard")
            if company.get("has_schema"):
                tags.append("schema")
            if company.get("has_landing"):
                tags.append("landing")
            if company.get("has_readme"):
                tags.append("docs")
            st.markdown(
                f'<span class="fc-chip">{escape(company.get("id", ""))}</span> '
                f'<span class="fc-muted">{escape(company.get("path", ""))} | {escape(", ".join(tags) or "sin artefactos fuertes")}</span>',
                unsafe_allow_html=True,
            )

        st.markdown("### Proyectos Para Portafolio")
        portfolio_items = []
        for project in projects:
            portfolio_items.append({
                "id": project.get("id"),
                "name": project.get("name"),
                "kind": "Ya en portafolio",
                "type": project.get("type"),
                "problem": project.get("problem"),
                "solution": project.get("solution"),
                "stack": project.get("stack", []),
                "outcomes": project.get("outcomes", []),
                "assets": ["2 screenshots limpios", "1 video demo corto", "link publico o nota de demo privada"],
                "value": "Proyecto base ya registrado.",
            })
        for candidate in candidates:
            portfolio_items.append({
                "id": candidate.get("id"),
                "name": candidate.get("name"),
                "kind": "Candidato nuevo",
                "type": candidate.get("type"),
                "problem": candidate.get("problem"),
                "solution": candidate.get("solution"),
                "stack": candidate.get("stack", []),
                "outcomes": candidate.get("outcomes", []),
                "assets": candidate.get("asset_recommendations", []),
                "value": candidate.get("portfolio_value"),
                "evidence": candidate.get("evidence", []),
            })

        if portfolio_items:
            tabs = st.tabs([str(item.get("name") or item.get("id"))[:28] for item in portfolio_items])
            for tab, item in zip(tabs, portfolio_items):
                with tab:
                    st.markdown(f"### {item.get('name')}")
                    st.caption(f"{item.get('kind')} | {item.get('type')} | {item.get('id')}")
                    st.write(item.get("problem", ""))
                    st.write(item.get("solution", ""))
                    if item.get("value"):
                        st.info(item.get("value"))
                    left, right = st.columns([1, 1])
                    with left:
                        st.markdown("**Stack / Skills comerciales**")
                        st.markdown("".join(f'<span class="fc-chip">{escape(str(s))}</span>' for s in item.get("stack", [])), unsafe_allow_html=True)
                        st.markdown("**Resultados / puntos para anunciar**")
                        for outcome in item.get("outcomes", []):
                            st.write(f"- {outcome}")
                    with right:
                        st.markdown("**Fotos/videos recomendados**")
                        for asset in item.get("assets", []):
                            st.write(f"- {asset}")
                        if item.get("evidence"):
                            st.markdown("**Evidencia en repo**")
                            for ev in item.get("evidence", []):
                                if ev:
                                    st.write(f"- {ev}")
        else:
            st.info("No hay proyectos/candidatos para mostrar.")

        st.markdown("### Recomendaciones Generales")
        st.markdown('<div class="fc-panel">', unsafe_allow_html=True)
        for rec in audit_data.get("recommendations", []):
            st.write(f"- {rec}")
        st.markdown("</div>", unsafe_allow_html=True)

    if gaps_data:
        st.markdown("### Gaps")
        st.json(gaps_data)

    audit_md = _read_text(PORTFOLIO_DIR / "factory_audit.md")
    if audit_md:
        with st.expander("Ver reporte Markdown"):
            st.text_area("factory_audit.md", value=audit_md, height=420)


def main() -> None:
    _render_hero()
    with st.sidebar:
        st.markdown("## Freelance Center")
        section = st.radio("Menu", ["Home", "Profile", "Portfolio", "Jobs", "Proposals", "Clients", "Audit", "Checklist"])
        if st.button("Actualizar"):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.caption(f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if section == "Home":
        _home()
    elif section == "Profile":
        _profile()
    elif section == "Portfolio":
        _portfolio()
    elif section == "Jobs":
        _jobs()
    elif section == "Proposals":
        _proposals()
    elif section == "Clients":
        _clients()
    elif section == "Audit":
        _audit()
    else:
        _checklist()


if __name__ == "__main__":
    main()
