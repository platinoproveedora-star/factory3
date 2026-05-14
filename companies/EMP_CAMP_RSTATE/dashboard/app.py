"""Streamlit dashboard for EMP_CAMP_RSTATE."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENV_PATH = ROOT / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from factory.dashboard_modules.campaign_ops import render_campaign_ops


st.set_page_config(page_title="RSTATE Campaign Dashboard", page_icon="F3", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    :root {
        --page: #f4f7fb;
        --surface: #ffffff;
        --surface-soft: #eef3f8;
        --ink: #111827;
        --muted: #5b677a;
        --line: #d6dee9;
        --accent: #0f766e;
        --accent-soft: #d9f3ee;
    }
    [data-testid="stAppViewContainer"] {
        background: var(--page);
    }
    [data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--line);
    }
    [data-testid="stHeader"] {
        background: rgba(244, 247, 251, 0.9);
    }
    h1, h2, h3, h4, p, li, label {
        color: var(--ink);
        letter-spacing: 0;
    }
    [data-testid="stCaptionContainer"] p {
        color: var(--muted);
    }
    a {
        color: #0b6fbd;
    }
    [data-testid="metric-container"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 8px 20px rgba(17, 24, 39, 0.06);
    }
    [data-testid="stExpander"] details {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
    }
    code, pre,
    [data-testid="stJson"] pre,
    [data-testid="stCodeBlock"] pre {
        color: var(--ink);
        background: #f8fafc;
        border: 1px solid var(--line);
        border-radius: 8px;
    }
    input, textarea, [role="combobox"] {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }
    .overview-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin: 18px 0 24px;
    }
    .overview-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px;
        min-height: 104px;
        box-shadow: 0 8px 20px rgba(17, 24, 39, 0.06);
    }
    .overview-card span {
        display: block;
        color: var(--muted);
        font-size: 13px;
        margin-bottom: 10px;
    }
    .overview-card strong {
        display: block;
        color: var(--ink);
        font-size: 22px;
        line-height: 1.2;
        overflow-wrap: anywhere;
    }
    .overview-hero {
        background: var(--surface);
        border: 1px solid var(--line);
        border-left: 5px solid var(--accent);
        border-radius: 8px;
        padding: 22px;
        margin: 0 0 18px;
        box-shadow: 0 8px 20px rgba(17, 24, 39, 0.06);
    }
    .overview-hero h1 {
        margin: 0 0 8px;
        color: var(--ink);
        font-size: 34px;
        line-height: 1.15;
    }
    .overview-hero p {
        margin: 0;
        color: var(--muted);
        font-size: 16px;
    }
    .overview-panel {
        background: var(--accent-soft);
        border: 1px solid #9bd7cc;
        border-radius: 8px;
        padding: 18px;
        margin-top: 12px;
    }
    .overview-panel p {
        color: #134e4a;
        margin: 0;
    }
    @media (max-width: 900px) {
        .overview-grid { grid-template-columns: 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _run_skill(nombre: str, context: dict, source: str = "internos") -> dict:
    from factory.engine import SkillLoader, SkillRunner

    base = ROOT / "factory"
    ext = base / "skills" / "externos"
    ext.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(
        internal_root=base / "skills" / "internos",
        external_root=ext,
        extra_roots={"meta": base / "skills" / "meta", "eval": base / "skills" / "eval"},
    )
    return SkillRunner(loader).run(nombre, context, source=source)


COMPANY_ID = os.getenv("EMPRESA_ID", "EMP_CAMP_RSTATE")
CAMPAIGN_SLUG = os.getenv("CAMPAIGN_SLUG", "first_rstate_campaign")

with st.sidebar:
    st.title("EMP_CAMP_RSTATE")
    page = st.radio("Menu", ["Overview", "Campaign Ops", "Docs"], label_visibility="collapsed")
    st.divider()
    if st.button("Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))


if page == "Overview":
    st.markdown(
        """
        <div class="overview-hero">
          <h1>RSTATE Campaign Dashboard</h1>
          <p>Centro operativo para campanas, assets, preflight, leads y resultados.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    config = _run_skill("vertical_companies/company_config_loader", {"company_id": COMPANY_ID})
    if config.get("ok"):
        data = config.get("data", {})
        cfg = data.get("config", {})
        cards = [
            ("Empresa", cfg.get("company_id", COMPANY_ID)),
            ("Industria", cfg.get("industry", "n/a")),
            ("Tipo", cfg.get("company_type", "n/a")),
        ]
        st.markdown(
            '<div class="overview-grid">'
            + "".join(
                f'<div class="overview-card"><span>{escape(label)}</span><strong>{escape(str(value))}</strong></div>'
                for label, value in cards
            )
            + "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="overview-panel">
              <p>Esta vista resume la empresa y deja el control operativo en Campaign Ops: preflight, uploads, leads y resultados.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Config", expanded=False):
            st.json(cfg)
    else:
        st.error(config.get("error", "No se pudo cargar configuracion"))

elif page == "Campaign Ops":
    render_campaign_ops(
        run_skill=_run_skill,
        company_id=COMPANY_ID,
        campaign_slug=CAMPAIGN_SLUG,
        default_bucket=os.getenv("CAMPAIGN_ASSETS_BUCKET", "campaign-assets"),
    )

elif page == "Docs":
    st.title("Docs")
    docs = [
        ROOT / "companies" / COMPANY_ID / "first_rstate_campaign.md",
        ROOT / "companies" / COMPANY_ID / "DASHBOARD_BRANCH.md",
        ROOT / "docs" / "DASHBOARD_CAMPAIGN_OPS.md",
    ]
    for path in docs:
        if path.exists():
            with st.expander(path.name, expanded=path.name == "first_rstate_campaign.md"):
                st.markdown(path.read_text(encoding="utf-8"))
