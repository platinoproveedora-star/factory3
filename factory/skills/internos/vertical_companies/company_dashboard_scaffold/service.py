from __future__ import annotations

import re
from pathlib import Path


_VALID_COMPANY_ID = re.compile(r"^[A-Z][A-Z0-9_]*$")


class CompanyDashboardScaffoldService:
    """Creates a Streamlit dashboard scaffold for a company.

    This is deterministic and focused on company dashboards. It complements
    `new_dashboard`, which is AI-generated and table-oriented.
    """

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not _VALID_COMPANY_ID.match(company_id):
            return {"ok": False, "error": "company_id debe usar MAYUSCULAS, numeros y _"}

        root = Path(__file__).resolve().parents[5]
        company_dir = root / "companies" / company_id
        if not company_dir.exists():
            return {"ok": False, "error": f"empresa no encontrada: {company_dir}"}

        output_dir = Path(context.get("output_dir") or company_dir / "dashboard")
        if not output_dir.is_absolute():
            output_dir = root / output_dir
        campaign_slug = str(context.get("campaign_slug") or "first_campaign").strip()
        title = str(context.get("title") or context.get("titulo") or f"{company_id} Dashboard").strip()
        service_name = str(context.get("render_service_name") or f"{company_id.lower().replace('_', '-')}-dashboard").strip()
        dry_run = context.get("dry_run", True)

        files = {
            output_dir / "app.py": self._app_py(title, company_id, campaign_slug),
            output_dir / "requirements.txt": self._requirements(),
            output_dir / "render.yaml": self._render_yaml(service_name, company_id, campaign_slug),
        }

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            for path, content in files.items():
                path.write_text(content, encoding="utf-8")

        return {
            "ok": True,
            "data": {
                "company_id": company_id,
                "output_dir": str(output_dir),
                "campaign_slug": campaign_slug,
                "dry_run": dry_run,
                "files": [str(path) for path in files],
            },
        }

    def _app_py(self, title: str, company_id: str, campaign_slug: str) -> str:
        return f'''"""Streamlit dashboard for {company_id}."""
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

from campaign_ops import render_campaign_ops


st.set_page_config(page_title="{title}", page_icon="F3", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    :root {{
        --page: #f4f7fb;
        --surface: #ffffff;
        --ink: #111827;
        --muted: #5b677a;
        --line: #d6dee9;
        --accent: #0f766e;
        --accent-soft: #d9f3ee;
    }}
    [data-testid="stAppViewContainer"] {{ background: var(--page); }}
    [data-testid="stSidebar"] {{
        background: var(--surface);
        border-right: 1px solid var(--line);
    }}
    [data-testid="stHeader"] {{ background: rgba(244, 247, 251, 0.9); }}
    h1, h2, h3, h4, p, li, label {{
        color: var(--ink);
        letter-spacing: 0;
    }}
    [data-testid="stCaptionContainer"] p {{ color: var(--muted); }}
    a {{ color: #0b6fbd; }}
    [data-testid="metric-container"] {{
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 8px 20px rgba(17, 24, 39, 0.06);
    }}
    [data-testid="stExpander"] details {{
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
    }}
    code, pre,
    [data-testid="stJson"] pre,
    [data-testid="stCodeBlock"] pre {{
        color: var(--ink);
        background: #f8fafc;
        border: 1px solid var(--line);
        border-radius: 8px;
    }}
    input, textarea, [role="combobox"] {{
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }}
    .overview-hero {{
        background: var(--surface);
        border: 1px solid var(--line);
        border-left: 5px solid var(--accent);
        border-radius: 8px;
        padding: 22px;
        margin: 0 0 18px;
        box-shadow: 0 8px 20px rgba(17, 24, 39, 0.06);
    }}
    .overview-hero h1 {{
        margin: 0 0 8px;
        color: var(--ink);
        font-size: 34px;
        line-height: 1.15;
    }}
    .overview-hero p {{
        margin: 0;
        color: var(--muted);
        font-size: 16px;
    }}
    .overview-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin: 18px 0 24px;
    }}
    .overview-card {{
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px;
        min-height: 104px;
        box-shadow: 0 8px 20px rgba(17, 24, 39, 0.06);
    }}
    .overview-card span {{
        display: block;
        color: var(--muted);
        font-size: 13px;
        margin-bottom: 10px;
    }}
    .overview-card strong {{
        display: block;
        color: var(--ink);
        font-size: 22px;
        line-height: 1.2;
        overflow-wrap: anywhere;
    }}
    .overview-panel {{
        background: var(--accent-soft);
        border: 1px solid #9bd7cc;
        border-radius: 8px;
        padding: 18px;
        margin-top: 12px;
    }}
    .overview-panel p {{
        color: #134e4a;
        margin: 0;
    }}
    @media (max-width: 900px) {{
        .overview-grid {{ grid-template-columns: 1fr; }}
    }}
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
        extra_roots={{"meta": base / "skills" / "meta", "eval": base / "skills" / "eval"}},
    )
    return SkillRunner(loader).run(nombre, context, source=source)


COMPANY_ID = os.getenv("EMPRESA_ID", "{company_id}")
CAMPAIGN_SLUG = os.getenv("CAMPAIGN_SLUG", "{campaign_slug}")

with st.sidebar:
    st.title("{company_id}")
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
          <h1>{title}</h1>
          <p>Centro operativo para campanas, assets, preflight, leads y resultados.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    config = _run_skill("vertical_companies/company_config_loader", {{"company_id": COMPANY_ID}})
    if config.get("ok"):
        data = config.get("data", {{}})
        cfg = data.get("config", {{}})
        cards = [
            ("Empresa", cfg.get("company_id", COMPANY_ID)),
            ("Industria", cfg.get("industry", "n/a")),
            ("Tipo", cfg.get("company_type", "n/a")),
        ]
        st.markdown(
            '<div class="overview-grid">'
            + "".join(
                f'<div class="overview-card"><span>{{escape(label)}}</span><strong>{{escape(str(value))}}</strong></div>'
                for label, value in cards
            )
            + "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="overview-panel">
              <p>Usa Campaign Ops para operar campanas: preflight, uploads, leads, resultados y settings.</p>
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
'''

    def _requirements(self) -> str:
        return "streamlit>=1.35\npandas>=2.0\n"

    def _render_yaml(self, service_name: str, company_id: str, campaign_slug: str) -> str:
        return f"""services:
  - type: web
    name: {service_name}
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
    envVars:
      - key: EMPRESA_ID
        value: {company_id}
      - key: CAMPAIGN_SLUG
        value: {campaign_slug}
      - key: CAMPAIGN_ASSETS_BUCKET
        value: campaign-assets
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: META_ACCESS_TOKEN
        sync: false
      - key: META_AD_ACCOUNT_ID
        sync: false
      - key: META_PAGE_ID
        sync: false
      - key: META_PRIVACY_URL
        sync: false
"""
