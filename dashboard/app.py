"""factory3 RH Dashboard — Streamlit."""

from __future__ import annotations

import os
from datetime import datetime

import streamlit as st
from db import count, select

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
.tag-seed { background:#3a3a5c; border-radius:4px; padding:2px 8px; font-size:12px; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏭 Factory3 RH")
    page = st.radio(
        "Sección",
        ["Overview", "Vacantes", "Candidatos", "Pipeline", "Seeds"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("↺ Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Actualizado: {datetime.utcnow().strftime('%H:%M:%S')} UTC")


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    colors = {
        "activa": "🟢", "pausada": "🟡", "cerrada": "🔴",
        "nuevo": "⚪", "apto": "🟢", "no_apto": "🔴",
        "listo_entrevista": "🔵", "rechazado": "🔴",
    }
    return f"{colors.get(estado, '⚫')} {estado}"


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Overview":
    st.title("Overview")

    vacantes   = _vacantes()
    candidatos = _candidatos()
    pipeline   = _pipeline()
    scores     = _scores()

    total_v     = len(vacantes)
    activas     = sum(1 for v in vacantes if v.get("estado") == "activa")
    total_c     = len(candidatos)
    aptos       = sum(1 for c in candidatos if c.get("estado") == "apto")
    seeds_v     = sum(1 for v in vacantes if v.get("tipo") == "seed")
    seeds_c     = sum(1 for c in candidatos if c.get("canal_user_id", "").startswith("test_") or c.get("canal_user_id", "").startswith("tg_"))
    avg_score   = (sum(s.get("score_total", 0) for s in scores) / len(scores)) if scores else 0
    pasan_ko    = sum(1 for s in scores if s.get("pasa_knockout"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vacantes activas", activas, f"{total_v} total")
    c2.metric("Candidatos", total_c, f"{aptos} aptos")
    c3.metric("Score promedio", f"{avg_score:.0f}", f"{pasan_ko} pasan KO")
    c4.metric("Seeds", seeds_v, "vacantes de prueba")

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
            df_etapas = pd.DataFrame({"Etapa": list(etapas.keys()), "Total": list(etapas.values())})
            st.bar_chart(df_etapas.set_index("Etapa"))
        else:
            st.info("Sin datos de pipeline")

    with col_b:
        st.subheader("Vacantes por tipo")
        tipos: dict[str, int] = {}
        for v in vacantes:
            t = v.get("tipo", "real")
            tipos[t] = tipos.get(t, 0) + 1
        if tipos:
            import pandas as pd
            df_tipos = pd.DataFrame({"Tipo": list(tipos.keys()), "Total": list(tipos.values())})
            st.bar_chart(df_tipos.set_index("Tipo"))
        else:
            st.info("Sin datos")

    st.divider()
    st.subheader("Últimas 5 vacantes")
    for v in vacantes[:5]:
        with st.container(border=True):
            cols = st.columns([1, 3, 1, 1])
            cols[0].caption(v.get("folio", "—"))
            cols[1].write(v.get("titulo", "—"))
            cols[2].write(_badge(v.get("estado", "—")))
            cols[3].caption(v.get("tipo", "real"))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Vacantes
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Vacantes":
    st.title("Vacantes")

    vacantes = _vacantes()

    col_f1, col_f2, col_f3 = st.columns(3)
    f_estado = col_f1.selectbox("Estado", ["Todos", "activa", "pausada", "cerrada"])
    f_tipo   = col_f2.selectbox("Tipo", ["Todos", "real", "seed"])
    f_buscar = col_f3.text_input("Buscar título")

    filtered = vacantes
    if f_estado != "Todos":
        filtered = [v for v in filtered if v.get("estado") == f_estado]
    if f_tipo != "Todos":
        filtered = [v for v in filtered if v.get("tipo") == f_tipo]
    if f_buscar:
        filtered = [v for v in filtered if f_buscar.lower() in (v.get("titulo") or "").lower()]

    st.caption(f"{len(filtered)} vacantes")

    for v in filtered:
        with st.expander(f"{v.get('folio','—')} — {v.get('titulo','—')} {_badge(v.get('estado',''))}"):
            c1, c2 = st.columns(2)
            c1.write(f"**Empresa:** {v.get('empresa_id','—')}")
            c1.write(f"**Canal:** {v.get('canal','—')}")
            c2.write(f"**Tipo:** {v.get('tipo','—')}")
            c2.write(f"**Creada:** {(v.get('created_at') or '')[:10]}")
            if v.get("descripcion"):
                st.write(v["descripcion"][:300])
            if isinstance(v.get("requisitos"), dict):
                st.json(v["requisitos"])


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Candidatos
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Candidatos":
    st.title("Candidatos")

    candidatos = _candidatos()
    scores_map = {s["candidato_id"]: s for s in _scores()}

    col_f1, col_f2 = st.columns(2)
    f_estado = col_f1.selectbox("Estado", ["Todos", "nuevo", "apto", "no_apto", "listo_entrevista", "rechazado"])
    f_buscar = col_f2.text_input("Buscar nombre / teléfono")

    filtered = candidatos
    if f_estado != "Todos":
        filtered = [c for c in filtered if c.get("estado") == f_estado]
    if f_buscar:
        filtered = [c for c in filtered if
                    f_buscar.lower() in (c.get("nombre") or "").lower() or
                    f_buscar in (c.get("telefono") or "")]

    st.caption(f"{len(filtered)} candidatos")

    import pandas as pd
    rows = []
    for c in filtered:
        sc = scores_map.get(c.get("id"), {})
        rows.append({
            "Folio":  c.get("folio", "—"),
            "Nombre": c.get("nombre", "—"),
            "Teléfono": c.get("telefono", "—"),
            "Estado": c.get("estado", "—"),
            "Score":  sc.get("score_total", "—"),
            "KO":     "✓" if sc.get("pasa_knockout") else "✗",
            "Creado": (c.get("created_at") or "")[:10],
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Sin resultados")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Pipeline":
    st.title("Pipeline")

    pipeline   = _pipeline()
    candidatos = {c["id"]: c for c in _candidatos()}
    vacantes   = {v["id"]: v for v in _vacantes()}

    etapas_ord = ["nuevo", "apto", "listo_entrevista", "rechazado", "no_apto"]
    by_etapa: dict[str, list] = {e: [] for e in etapas_ord}

    for p in pipeline:
        e = p.get("etapa", "nuevo")
        if e not in by_etapa:
            by_etapa[e] = []
        by_etapa[e].append(p)

    cols = st.columns(len(etapas_ord))
    for col, etapa in zip(cols, etapas_ord):
        items = by_etapa.get(etapa, [])
        col.markdown(f"**{etapa.upper()}** `{len(items)}`")
        for p in items[:20]:
            cand = candidatos.get(p.get("candidato_id"), {})
            vac  = vacantes.get(p.get("vacante_id"), {})
            col.container(border=True).write(
                f"**{cand.get('folio','?')}** {cand.get('nombre','?')}\n\n"
                f"_{vac.get('titulo','?')[:30]}_"
            )
        if len(items) > 20:
            col.caption(f"... y {len(items)-20} más")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Seeds
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Seeds":
    st.title("Seeds de prueba")

    seeds = _seeds()

    # Group by seed_label
    by_label: dict[str, dict] = {}
    for s in seeds:
        lbl = s.get("seed_label", "?")
        if lbl not in by_label:
            by_label[lbl] = {"empresa": s.get("empresa_id", "?"), "rows": [], "created_at": s.get("created_at", "")}
        by_label[lbl]["rows"].append(s)

    st.caption(f"{len(by_label)} seeds registrados")

    for label, info in list(by_label.items())[:30]:
        tabla_counts: dict[str, int] = {}
        for r in info["rows"]:
            t = r.get("tabla", "?")
            tabla_counts[t] = tabla_counts.get(t, 0) + 1

        summary = "  ".join(f"`{t}:{n}`" for t, n in tabla_counts.items())
        with st.expander(f"**{label}** — {(info['created_at'] or '')[:10]}  {summary}"):
            st.write(f"**Empresa:** {info['empresa']}")
            import pandas as pd
            df = pd.DataFrame([
                {"Tabla": t, "Registros": n} for t, n in tabla_counts.items()
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
