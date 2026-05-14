"""Streamlit dashboard for EMP_CAMP_RSTATE."""
from __future__ import annotations

import os
import sys
from datetime import datetime
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
    [data-testid="stAppViewContainer"] { background: #0f1115; }
    [data-testid="stSidebar"] { background: #151821; }
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] li,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] span,
    [data-testid="stAppViewContainer"] div {
        color: #eef2fb;
    }
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #f5f7fc;
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
        color: #cbd5e1;
    }
    [data-testid="metric-container"] {
        background: #1b2030;
        border: 1px solid #2a3145;
        border-radius: 8px;
        padding: 12px;
    }
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricValue"] div {
        color: #ffffff;
    }
    h1, h2, h3, h4 { color: #ffffff; }
    code, pre {
        color: #f8fafc;
        background: #171b26;
    }
    [data-testid="stJson"],
    [data-testid="stJson"] *,
    [data-testid="stCodeBlock"],
    [data-testid="stCodeBlock"] *,
    [data-testid="stExpander"],
    [data-testid="stExpander"] * {
        color: #f8fafc;
    }
    [data-testid="stJson"] pre,
    [data-testid="stCodeBlock"] pre {
        background: #111827;
        border: 1px solid #334155;
        border-radius: 8px;
    }
    [data-testid="stExpander"] details {
        background: #151b28;
        border: 1px solid #334155;
        border-radius: 8px;
    }
    a { color: #8ec5ff; }
    [data-testid="stDataFrame"] {
        color: #f8fafc;
    }
    div[data-baseweb="input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="select"] > div {
        background: #ffffff;
        border-color: #cbd5e1;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }
    div[data-baseweb="input"] input::placeholder,
    div[data-baseweb="textarea"] textarea::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
    }
    [role="listbox"],
    [role="option"] {
        background: #ffffff;
        color: #111827 !important;
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
    st.title("RSTATE Campaign Dashboard")
    st.caption("Dashboard de empresa para operar campanas, assets, preflight, leads y resultados.")
    config = _run_skill("vertical_companies/company_config_loader", {"company_id": COMPANY_ID})
    if config.get("ok"):
        data = config.get("data", {})
        cfg = data.get("config", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Empresa", cfg.get("company_id", COMPANY_ID))
        c2.metric("Industria", cfg.get("industry", "n/a"))
        c3.metric("Tipo", cfg.get("company_type", "n/a"))
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
