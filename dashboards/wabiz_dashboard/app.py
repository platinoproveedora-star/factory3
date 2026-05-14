"""Factory3 WhatsApp Dashboard — Streamlit app."""
from __future__ import annotations

import os

import streamlit as st

from db import select

st.set_page_config(page_title="Factory3 WhatsApp Dashboard", page_icon="🏭", layout="wide")

st.markdown(
    '<style>[data-testid="metric-container"]{background:#1e1e2e;border-radius:8px;padding:12px;}'
    '[data-testid="stSidebar"]{background:#12121c;}'
    'h1,h2,h3{color:#e0e0ff;}</style>',
    unsafe_allow_html=True,
)

_EMPRESA_ID = os.getenv("WABIZ_EMPRESA_ID", "empresa_demo")


def _badge(estado: str) -> str:
    e = str(estado).lower()
    if e in ("activa", "apto"):
        return f"🟢 {estado}"
    if e == "pausada":
        return f"🟡 {estado}"
    if e in ("cerrada", "no_apto", "rechazado"):
        return f"🔴 {estado}"
    if e == "contratado":
        return f"🏆 {estado}"
    return estado


def _folio(row: dict, prefix: str) -> str:
    if "folio" in row and row["folio"]:
        return str(row["folio"])
    raw_id = str(row.get("id", ""))
    return f"{prefix}{raw_id[:6]}..."


@st.cache_data(ttl=30)
def _load_wabiz_config() -> list[dict]:
    return select("wabiz_config", empresa_id=_EMPRESA_ID)


@st.cache_data(ttl=30)
def _load_wabiz_messages() -> list[dict]:
    return select("wabiz_messages", empresa_id=_EMPRESA_ID)


def _section_overview() -> None:
    import pandas as pd

    st.title("🏭 Factory3 WhatsApp Dashboard")
    st.caption(f"Empresa: `{_EMPRESA_ID}`")
    st.markdown("---")

    config_rows = _load_wabiz_config()
    messages_rows = _load_wabiz_messages()

    c1, c2 = st.columns(2)
    with c1:
        st.metric("⚙️ wabiz_config", len(config_rows))
    with c2:
        st.metric("💬 wabiz_messages", len(messages_rows))

    st.markdown("---")
    st.subheader("Actividad reciente — wabiz_messages")

    if messages_rows:
        df = pd.DataFrame(messages_rows)
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
            df = df.sort_values("created_at", ascending=False)
        st.dataframe(df.head(10), use_container_width=True)
    else:
        st.info("Sin mensajes recientes.")


def _section_wabiz_config() -> None:
    import pandas as pd

    st.header("⚙️ Configuración (wabiz_config)")

    rows = _load_wabiz_config()
    if not rows:
        st.warning("Sin registros en wabiz_config.")
        return

    df = pd.DataFrame(rows)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    tab_tabla, tab_detalle = st.tabs(["📋 Tabla", "🔍 Detalle"])

    with tab_tabla:
        buscar = st.text_input("🔎 Buscar en config", key="cfg_buscar")
        if buscar:
            mask = df.apply(lambda r: r.astype(str).str.contains(buscar, case=False).any(), axis=1)
            df_view = df[mask]
        else:
            df_view = df

        st.caption(f"{len(df_view)} registros")
        st.dataframe(df_view, use_container_width=True)

    with tab_detalle:
        if df.empty:
            st.info("Sin datos.")
        else:
            ids = df["id"].astype(str).tolist()
            sel = st.selectbox("Selecciona un registro", ids, key="cfg_sel")
            row = df[df["id"].astype(str) == sel].iloc[0].to_dict()
            with st.expander("Campos del registro", expanded=True):
                for k, v in row.items():
                    st.text_input(k, value=str(v), disabled=True, key=f"cfg_field_{k}")


def _section_wabiz_messages() -> None:
    import pandas as pd

    st.header("💬 Mensajes (wabiz_messages)")

    rows = _load_wabiz_messages()
    if not rows:
        st.warning("Sin registros en wabiz_messages.")
        return

    df = pd.DataFrame(rows)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.sort_values("created_at", ascending=False)

    tab_tabla, tab_detalle = st.tabs(["📋 Tabla", "🔍 Detalle"])

    with tab_tabla:
        buscar = st.text_input("🔎 Buscar en mensajes", key="msg_buscar")
        if buscar:
            mask = df.apply(lambda r: r.astype(str).str.contains(buscar, case=False).any(), axis=1)
            df_view = df[mask]
        else:
            df_view = df

        st.caption(f"{len(df_view)} registros")
        st.dataframe(df_view, use_container_width=True)

    with tab_detalle:
        if df.empty:
            st.info("Sin datos.")
        else:
            ids = df["id"].astype(str).tolist()
            sel = st.selectbox("Selecciona un mensaje", ids, key="msg_sel")
            row = df[df["id"].astype(str) == sel].iloc[0].to_dict()
            folio = _folio(row, "MSG-")
            st.caption(f"Folio: **{folio}**")
            with st.expander("Campos del mensaje", expanded=True):
                for k, v in row.items():
                    st.text_input(k, value=str(v), disabled=True, key=f"msg_field_{k}")


_SECTIONS = {
    "🏠 Overview": _section_overview,
    "⚙️ wabiz_config": _section_wabiz_config,
    "💬 wabiz_messages": _section_wabiz_messages,
}

with st.sidebar:
    st.markdown("## 🏭 Factory3")
    st.markdown(f"**Empresa:** `{_EMPRESA_ID}`")
    st.markdown("---")
    seccion = st.radio("Navegar", list(_SECTIONS.keys()), label_visibility="collapsed")
    st.markdown("---")
    if st.button("↺ Actualizar"):
        st.cache_data.clear()
        st.rerun()

_SECTIONS[seccion]()