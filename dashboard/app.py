"""factory3 RH Dashboard — Streamlit."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

import streamlit as st

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

_API = os.getenv("FACTORY_API_URL", "http://localhost:8000").rstrip("/")


# ── Data layer ────────────────────────────────────────────────────────────────

def _call(skill: str, params: dict | None = None) -> dict:
    qs = urllib.parse.urlencode(params or {})
    url = f"{_API}/data/{skill}{'?' + qs if qs else ''}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as exc:
        return {"_error": str(exc)}


@st.cache_data(ttl=30)
def _stats() -> dict:
    return _call("rh_stats")

@st.cache_data(ttl=30)
def _vacantes(estado: str = "", tipo: str = "", buscar: str = "") -> dict:
    p: dict = {}
    if estado: p["estado"] = estado
    if tipo:   p["tipo"]   = tipo
    if buscar: p["buscar"] = buscar
    return _call("rh_list_vacantes", p)

@st.cache_data(ttl=30)
def _pipeline(vacante_id: str = "") -> dict:
    p: dict = {}
    if vacante_id: p["vacante_id"] = vacante_id
    return _call("rh_pipeline_view", p)

@st.cache_data(ttl=30)
def _candidatos_raw() -> list:
    from db import select
    return select("candidatos", "select=*&order=created_at.desc&limit=500")

@st.cache_data(ttl=30)
def _scores_raw() -> list:
    from db import select
    return select("scores", "select=candidato_id,score_total,pasa_knockout&limit=500")

@st.cache_data(ttl=30)
def _seeds_raw() -> list:
    from db import select
    return select("test_seeds", "select=seed_label,tabla,empresa_id,created_at&order=created_at.desc&limit=1000")


def _badge(estado: str) -> str:
    icons = {
        "activa": "🟢", "pausada": "🟡", "cerrada": "🔴",
        "nuevo": "⚪", "apto": "🟢", "no_apto": "🔴",
        "listo_entrevista": "🔵", "rechazado": "🔴", "contratado": "🏆",
    }
    return f"{icons.get(estado, '⚫')} {estado}"


# ── Sidebar ───────────────────────────────────────────────────────────────────

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
    st.caption(f"API: `{_API}`")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Overview":
    st.title("Overview")

    kpis = _stats()
    if "_error" in kpis:
        st.error(f"No se pudo conectar al API: {kpis['_error']}")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vacantes activas",  kpis.get("vacantes_activas", 0),  f"{kpis.get('vacantes_total', 0)} total")
    c2.metric("Candidatos",        kpis.get("candidatos_total", 0),  f"{kpis.get('candidatos_aptos', 0)} aptos")
    c3.metric("Score promedio",    kpis.get("score_promedio", 0),     f"{kpis.get('pasan_knockout', 0)} pasan KO")
    c4.metric("Seeds",             kpis.get("seeds_total", 0),        f"{kpis.get('vacantes_seed', 0)} vacantes")

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Candidatos por etapa")
        pipeline = _pipeline()
        totales  = pipeline.get("totales", {})
        if any(totales.values()):
            import pandas as pd
            df = pd.DataFrame({"Etapa": list(totales.keys()), "Total": list(totales.values())})
            st.bar_chart(df[df["Total"] > 0].set_index("Etapa"))
        else:
            st.info("Sin datos de pipeline")

    with col_b:
        st.subheader("Vacantes recientes")
        vacs = _vacantes()
        for v in (vacs.get("rows") or [])[:5]:
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

    col_f1, col_f2, col_f3 = st.columns(3)
    f_estado = col_f1.selectbox("Estado", ["", "activa", "pausada", "cerrada"], format_func=lambda x: "Todos" if not x else x)
    f_tipo   = col_f2.selectbox("Tipo",   ["", "real", "seed"],                  format_func=lambda x: "Todos" if not x else x)
    f_buscar = col_f3.text_input("Buscar título")

    result = _vacantes(f_estado, f_tipo, f_buscar)
    rows   = result.get("rows") or []
    st.caption(f"{len(rows)} vacantes")

    for v in rows:
        with st.expander(f"{v.get('folio','—')} — {v.get('titulo','—')}  {_badge(v.get('estado',''))}"):
            c1, c2 = st.columns(2)
            c1.write(f"**Canal:** {v.get('canal','—')}")
            c2.write(f"**Tipo:** {v.get('tipo','—')}")
            c2.write(f"**Creada:** {(v.get('created_at') or '')[:10]}")
            if v.get("descripcion"):
                st.write(v["descripcion"][:300])


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Candidatos
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Candidatos":
    st.title("Candidatos")

    candidatos = _candidatos_raw()
    scores_map = {s["candidato_id"]: s for s in _scores_raw()}

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
            "Folio":    c.get("folio", "—"),
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
# PAGE: Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Pipeline":
    st.title("Pipeline")

    pipeline = _pipeline()
    by_etapa = pipeline.get("by_etapa", {})
    etapas   = pipeline.get("etapas", [])

    cols = st.columns(max(len(etapas), 1))
    for col, etapa in zip(cols, etapas):
        items = by_etapa.get(etapa, [])
        col.markdown(f"**{etapa.upper()}** `{len(items)}`")
        for p in items[:20]:
            col.container(border=True).write(
                f"**{p.get('candidato_folio','?')}** {p.get('candidato_nombre','?')}\n\n"
                f"_{p.get('vacante_titulo','?')[:30]}_"
            )
        if len(items) > 20:
            col.caption(f"... y {len(items)-20} más")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Seeds
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Seeds":
    st.title("Seeds de prueba")

    seeds = _seeds_raw()
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
            df = pd.DataFrame([{"Tabla": t, "Registros": n} for t, n in tabla_counts.items()])
            st.dataframe(df, use_container_width=True, hide_index=True)
