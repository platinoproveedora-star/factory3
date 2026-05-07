"""factory3 RH Dashboard — Streamlit."""
from __future__ import annotations

import os
from datetime import datetime

import streamlit as st
from db import select

st.set_page_config(
    page_title="Factory3 RH Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
[data-testid="metric-container"] { background:#1e1e2e; border-radius:8px; padding:12px; }
[data-testid="stSidebar"] { background:#12121c; }
h1,h2,h3 { color:#e0e0ff; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")


# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _vacantes():
    return select("vacantes", "select=*&order=created_at.desc&limit=200")

@st.cache_data(ttl=30)
def _candidatos():
    return select("candidatos", "select=*&order=created_at.desc&limit=500")

@st.cache_data(ttl=30)
def _pipeline():
    return select("pipeline", "select=*&order=created_at.desc&limit=500")

@st.cache_data(ttl=30)
def _scores():
    return select("scores", "select=candidato_id,score_total,pasa_knockout&limit=500")

@st.cache_data(ttl=30)
def _seeds():
    return select("test_seeds", "select=seed_label,tabla,empresa_id,created_at&order=created_at.desc&limit=1000")


def _badge(estado: str) -> str:
    icons = {
        "activa": "🟢", "pausada": "🟡", "cerrada": "🔴",
        "nuevo": "⚪", "apto": "🟢", "no_apto": "🔴",
        "listo_entrevista": "🔵", "rechazado": "🔴", "contratado": "🏆",
    }
    return f"{icons.get(estado, '⚫')} {estado}"

def _folio(row: dict, prefix: str = "") -> str:
    f = row.get("folio")
    if f:
        return f
    uid = row.get("id", "")
    return f"{prefix}{uid[:6]}..." if uid else "—"


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏭 Factory3 RH")
    page = st.radio("Sección", ["Overview", "Vacantes", "Candidatos", "Pipeline", "Seeds"],
                    label_visibility="collapsed")
    st.divider()
    if st.button("↺ Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Actualizado: {datetime.utcnow().strftime('%H:%M:%S')} UTC")


# ═══════════════════════════════════════════════════════════════════════════════
# Overview
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Overview":
    st.title("Overview")

    vacantes   = _vacantes()
    candidatos = _candidatos()
    scores     = _scores()
    pipeline   = _pipeline()
    seeds      = _seeds()

    activas   = sum(1 for v in vacantes if v.get("estado") == "activa")
    seeds_v   = sum(1 for v in vacantes if v.get("tipo") == "seed")
    aptos     = sum(1 for c in candidatos if c.get("estado") == "apto")
    avg_score = round(sum(s.get("score_total", 0) for s in scores) / len(scores), 1) if scores else 0
    pasan_ko  = sum(1 for s in scores if s.get("pasa_knockout"))
    labels    = {r.get("seed_label") for r in seeds}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vacantes activas",  activas,          f"{len(vacantes)} total")
    c2.metric("Candidatos",        len(candidatos),   f"{aptos} aptos")
    c3.metric("Score promedio",    avg_score,         f"{pasan_ko} pasan KO")
    c4.metric("Seeds",             len(labels),       f"{seeds_v} vacantes seed")

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Candidatos por etapa")
        etapas: dict[str, int] = {}
        for p in pipeline:
            e = p.get("etapa", "sin_etapa")
            etapas[e] = etapas.get(e, 0) + 1
        if etapas:
            import pandas as pd
            df = pd.DataFrame({"Etapa": list(etapas.keys()), "Total": list(etapas.values())})
            st.bar_chart(df[df["Total"] > 0].set_index("Etapa"))
        else:
            st.info("Sin datos de pipeline")

    with col_b:
        st.subheader("Vacantes recientes")
        for v in vacantes[:5]:
            with st.container(border=True):
                cols = st.columns([1, 3, 1, 1])
                cols[0].caption(_folio(v, "V-"))
                cols[1].write(v.get("titulo", "—"))
                cols[2].write(_badge(v.get("estado", "—")))
                cols[3].caption(v.get("tipo", "real"))


# ═══════════════════════════════════════════════════════════════════════════════
# Vacantes
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Vacantes":
    st.title("Vacantes")

    vacantes = _vacantes()
    col_f1, col_f2, col_f3 = st.columns(3)
    f_estado = col_f1.selectbox("Estado", ["", "activa", "pausada", "cerrada"], format_func=lambda x: "Todos" if not x else x)
    f_tipo   = col_f2.selectbox("Tipo",   ["", "real", "seed"],                  format_func=lambda x: "Todos" if not x else x)
    f_buscar = col_f3.text_input("Buscar título")

    filtered = vacantes
    if f_estado: filtered = [v for v in filtered if v.get("estado") == f_estado]
    if f_tipo:   filtered = [v for v in filtered if v.get("tipo") == f_tipo]
    if f_buscar: filtered = [v for v in filtered if f_buscar.lower() in (v.get("titulo") or "").lower()]

    st.caption(f"{len(filtered)} vacantes")
    for v in filtered:
        with st.expander(f"{_folio(v,'V-')} — {v.get('titulo','—')}  {_badge(v.get('estado',''))}"):
            c1, c2 = st.columns(2)
            c1.write(f"**Canal:** {v.get('canal','—')}")
            c1.write(f"**Empresa:** {v.get('empresa_id','—')}")
            c2.write(f"**Tipo:** {v.get('tipo','—')}")
            c2.write(f"**Creada:** {(v.get('created_at') or '')[:10]}")
            if v.get("descripcion"):
                st.write(v["descripcion"][:300])


# ═══════════════════════════════════════════════════════════════════════════════
# Candidatos
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Candidatos":
    st.title("Candidatos")

    candidatos = _candidatos()
    scores_map = {s["candidato_id"]: s for s in _scores()}

    col_f1, col_f2 = st.columns(2)
    f_estado = col_f1.selectbox("Estado", ["Todos", "nuevo", "apto", "no_apto", "listo_entrevista", "rechazado"])
    f_buscar = col_f2.text_input("Buscar nombre / teléfono")

    filtered = candidatos
    if f_estado != "Todos": filtered = [c for c in filtered if c.get("estado") == f_estado]
    if f_buscar: filtered = [c for c in filtered if
                             f_buscar.lower() in (c.get("nombre") or "").lower() or
                             f_buscar in (c.get("telefono") or "")]

    st.caption(f"{len(filtered)} candidatos")
    import pandas as pd
    rows = []
    for c in filtered:
        sc = scores_map.get(c.get("id"), {})
        rows.append({
            "Folio":    _folio(c, "C-"),
            "Nombre":   c.get("nombre", "—"),
            "Teléfono": c.get("telefono", "—"),
            "Estado":   c.get("estado", "—"),
            "Score":    sc.get("score_total", "—"),
            "KO":       "✓" if sc.get("pasa_knockout") else "✗",
            "Creado":   (c.get("created_at") or "")[:10],
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Sin resultados")


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Pipeline":
    st.title("Pipeline")

    pipeline  = _pipeline()
    cands_map = {c["id"]: c for c in _candidatos()}
    vacs_map  = {v["id"]: v for v in _vacantes()}

    etapas_ord = ["nuevo", "apto", "listo_entrevista", "rechazado", "no_apto", "contratado"]
    by_etapa: dict[str, list] = {e: [] for e in etapas_ord}
    for p in pipeline:
        e = p.get("etapa", "nuevo")
        if e not in by_etapa:
            by_etapa[e] = []
        by_etapa[e].append(p)

    # Tabs en lugar de columnas — más limpio
    tabs = st.tabs([f"{e.upper()} ({len(by_etapa.get(e,[]))})" for e in etapas_ord])
    for tab, etapa in zip(tabs, etapas_ord):
        with tab:
            items = by_etapa.get(etapa, [])
            if not items:
                st.info("Sin candidatos en esta etapa")
                continue
            import pandas as pd
            rows = []
            for p in items:
                cand = cands_map.get(p.get("candidato_id"), {})
                vac  = vacs_map.get(p.get("vacante_id"), {})
                rows.append({
                    "Candidato": _folio(cand, "C-"),
                    "Nombre":    cand.get("nombre", "—"),
                    "Vacante":   _folio(vac, "V-"),
                    "Puesto":    (vac.get("titulo") or "—")[:40],
                    "Notas":     (p.get("notas") or "")[:50],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Seeds
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Seeds":
    st.title("Seeds de prueba")

    seeds = _seeds()
    by_label: dict[str, dict] = {}
    for s in seeds:
        lbl = s.get("seed_label", "?")
        if lbl not in by_label:
            by_label[lbl] = {"empresa": s.get("empresa_id", "?"), "rows": [], "created_at": s.get("created_at", "")}
        by_label[lbl]["rows"].append(s)

    st.caption(f"{len(by_label)} seeds registrados")

    if not by_label:
        st.info("No hay seeds registrados")
    else:
        for label, info in list(by_label.items())[:30]:
            tabla_counts: dict[str, int] = {}
            for r in info["rows"]:
                t = r.get("tabla", "?")
                tabla_counts[t] = tabla_counts.get(t, 0) + 1
            summary = "  ".join(f"`{t}:{n}`" for t, n in tabla_counts.items())
            with st.expander(f"**{label}** — {(info['created_at'] or '')[:10]}  {summary}"):
                st.write(f"**Empresa:** {info['empresa']}")
                import pandas as pd
                df = pd.DataFrame([{"Tabla": t, "Registros": n} for t, n in tabla_counts.items()])
                st.dataframe(df, use_container_width=True, hide_index=True)
