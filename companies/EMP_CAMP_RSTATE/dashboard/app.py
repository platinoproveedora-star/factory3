"""Streamlit dashboard for EMP_CAMP_RSTATE."""
from __future__ import annotations

import base64
import json
import os
import re
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
ASSETS_BUCKET = os.getenv("CAMPAIGN_ASSETS_BUCKET", "campaign-assets")
ASSETS_FOLDER = f"{COMPANY_ID}/{CAMPAIGN_SLUG}"
SUPABASE_PUBLIC_URL = os.getenv("SUPABASE_URL", "").rstrip("/")


def _safe_filename(name: str) -> str:
    stem = Path(name).stem.lower()
    suffix = Path(name).suffix.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "asset"
    return f"{stem}{suffix}"


def _storage_url(bucket: str, path: str) -> str:
    if not SUPABASE_PUBLIC_URL:
        return path
    return f"{SUPABASE_PUBLIC_URL}/storage/v1/object/public/{bucket}/{path}"


def _upload_bytes(path: str, content: bytes, content_type: str) -> dict:
    return _run_skill(
        "supabase_storage_upload",
        {
            "bucket": ASSETS_BUCKET,
            "path": path,
            "content_b64": base64.b64encode(content).decode("ascii"),
            "content_type": content_type,
            "dry_run": False,
        },
        "internos",
    )


def _render_landing_page() -> None:
    st.markdown(
        """
        <div class="overview-hero">
          <h1>Landing Page</h1>
          <p>Configura la imagen principal y el carrete de fotos que se muestra en la landing publica.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Destino storage: {ASSETS_BUCKET}/{ASSETS_FOLDER}")

    main_image = st.file_uploader(
        "Imagen principal",
        type=["jpg", "jpeg", "png", "webp"],
        key="landing_main_image",
    )
    gallery_images = st.file_uploader(
        "Carrete de fotos del inmueble (1 a 6 imagenes)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="landing_gallery_images",
    )
    if gallery_images and len(gallery_images) > 6:
        st.warning("Solo se usaran las primeras 6 imagenes del carrete.")

    current_config_url = _storage_url(ASSETS_BUCKET, f"{ASSETS_FOLDER}/landing_config.json")
    st.text_input("Landing config publica", value=current_config_url, disabled=True)

    if st.button("Guardar fotos en landing", type="primary", use_container_width=True):
        uploaded_main_url = ""
        gallery_urls = []
        diagnostics = []

        if main_image:
            path = f"{ASSETS_FOLDER}/landing/main-{_safe_filename(main_image.name)}"
            result = _upload_bytes(path, main_image.getvalue(), main_image.type or "application/octet-stream")
            diagnostics.append({"file": main_image.name, "role": "main", **result})
            if result.get("ok"):
                uploaded_main_url = result.get("data", {}).get("url") or _storage_url(ASSETS_BUCKET, path)

        for file in (gallery_images or [])[:6]:
            path = f"{ASSETS_FOLDER}/landing/gallery-{_safe_filename(file.name)}"
            result = _upload_bytes(path, file.getvalue(), file.type or "application/octet-stream")
            diagnostics.append({"file": file.name, "role": "gallery", **result})
            if result.get("ok"):
                gallery_urls.append(result.get("data", {}).get("url") or _storage_url(ASSETS_BUCKET, path))

        if not uploaded_main_url and gallery_urls:
            uploaded_main_url = gallery_urls[0]

        config = {
            "company_id": COMPANY_ID,
            "campaign_slug": CAMPAIGN_SLUG,
            "main_image_url": uploaded_main_url,
            "gallery_urls": gallery_urls,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        config_result = _upload_bytes(
            f"{ASSETS_FOLDER}/landing_config.json",
            json.dumps(config, ensure_ascii=True, indent=2).encode("utf-8"),
            "application/json",
        )
        diagnostics.append({"file": "landing_config.json", "role": "config", **config_result})
        st.session_state["landing_config"] = config
        st.session_state["landing_diagnostics"] = diagnostics

        if config_result.get("ok"):
            st.success("Landing config actualizada. Refresca la landing publica para ver las nuevas fotos.")
        else:
            st.error(config_result.get("error", "No se pudo guardar landing_config.json"))

    if st.session_state.get("landing_config"):
        cfg = st.session_state["landing_config"]
        st.subheader("Vista rapida")
        if cfg.get("main_image_url"):
            st.image(cfg["main_image_url"], caption="Imagen principal", use_container_width=True)
        if cfg.get("gallery_urls"):
            cols = st.columns(min(3, len(cfg["gallery_urls"])))
            for index, url in enumerate(cfg["gallery_urls"]):
                cols[index % len(cols)].image(url, caption=f"Foto {index + 1}", use_container_width=True)
        st.json(cfg, expanded=False)

    if st.session_state.get("landing_diagnostics"):
        with st.expander("Diagnostico de subida", expanded=False):
            st.json(st.session_state["landing_diagnostics"], expanded=False)

with st.sidebar:
    st.title("EMP_CAMP_RSTATE")
    page = st.radio("Menu", ["Overview", "Campaign Ops", "Landing Page", "Docs"], label_visibility="collapsed")
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

elif page == "Landing Page":
    _render_landing_page()

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
