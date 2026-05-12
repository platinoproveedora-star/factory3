"""factory3 RH Dashboard — Streamlit."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

# Carga .env si existe (desarrollo local)
_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            if _k.strip() not in os.environ:
                os.environ[_k.strip()] = _v.strip()

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
[data-testid="stSidebar"] * { color:#ffffff !important; }
[data-testid="stSidebar"] .stRadio label { color:#ffffff !important; }
[data-testid="stSidebar"] p { color:#ffffff !important; }
[data-testid="stSidebar"] span { color:#ffffff !important; }
h1,h2,h3 { color:#e0e0ff; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")


def _run_skill(nombre: str, context: dict, source: str = "internos") -> dict:
    import sys
    _root = str(Path(__file__).parent.parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from factory.engine import SkillLoader, SkillRunner
    _base = Path(__file__).parent.parent.parent / "factory"
    ext = _base / "skills" / "externos"
    ext.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(internal_root=_base / "skills" / "internos", external_root=ext)
    # meta/eval: pasar ruta absoluta como source (SkillLoader fallback: Path(source)/name)
    if source == "meta":
        source = str(_base / "skills" / "meta")
    elif source == "eval":
        source = str(_base / "skills" / "eval")
    return SkillRunner(loader).run(nombre, context, source=source)


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

@st.cache_data(ttl=30)
def _entrevistas():
    return select("entrevistas", "select=*&order=created_at.desc&limit=500")

@st.cache_data(ttl=30)
def _reclutadores():
    return select("reclutadores", "select=*&order=nombre.asc&limit=200")

@st.cache_data(ttl=30)
def _scores_full():
    return select("scores", "select=*&order=created_at.desc&limit=500")

@st.cache_data(ttl=30)
def _ultima_vacante():
    return select("vacantes", "select=*&order=created_at.desc&limit=1")

@st.cache_data(ttl=30)
def _candidatos_vacante(vid):
    return select("candidatos", f"select=*&vacante_id=eq.{vid}")

@st.cache_data(ttl=30)
def _scores_vacante(vid):
    return select("scores", f"select=*&vacante_id=eq.{vid}")

@st.cache_data(ttl=30)
def _pipeline_vacante(vid):
    return select("pipeline", f"select=*&vacante_id=eq.{vid}&order=created_at.desc")

@st.cache_data(ttl=30)
def _respuestas_vacante(vid):
    return select("respuestas", f"select=*&vacante_id=eq.{vid}&order=candidato_id,orden")


def _badge(estado: str) -> str:
    icons = {
        "activa": "🟢", "pausada": "🟡", "cerrada": "🔴",
        "nuevo": "⚪", "apto": "🟢", "no_apto": "🔴",
        "listo_entrevista": "🔵", "rechazado": "🔴", "contratado": "🏆",
        "agendada": "🟡", "cancelada": "🔴", "realizada": "🟢",
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
    page = st.radio(
        "Sección",
        ["Overview", "Vacantes", "Candidatos", "Pipeline", "Entrevistas", "Reclutadores", "Seeds", "Ultima Vacante", "Análisis IA", "Offer Builder", "FB Groups", "Tasks", "Meta Skills", "SAT"],
        label_visibility="collapsed",
    )
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

    vacantes     = _vacantes()
    candidatos   = _candidatos()
    scores       = _scores()
    pipeline     = _pipeline()
    seeds        = _seeds()
    entrevistas  = _entrevistas()
    reclutadores = _reclutadores()

    activas   = sum(1 for v in vacantes if v.get("estado") == "activa")
    seeds_v   = sum(1 for v in vacantes if v.get("tipo") == "seed")
    aptos     = sum(1 for c in candidatos if c.get("estado") == "apto")
    avg_score = round(sum(s.get("score_total", 0) for s in scores) / len(scores), 1) if scores else 0
    pasan_ko  = sum(1 for s in scores if s.get("pasa_knockout"))
    labels    = {r.get("seed_label") for r in seeds}

    # ── Fila 1 ────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vacantes activas",  activas,          f"{len(vacantes)} total")
    c2.metric("Candidatos",        len(candidatos),   f"{aptos} aptos")
    c3.metric("Score promedio",    avg_score,         f"{pasan_ko} pasan KO")
    c4.metric("Seeds",             len(labels),       f"{seeds_v} vacantes seed")

    # ── Fila 2 ────────────────────────────────────────────────────────────────
    entrevistas_agendadas  = sum(1 for e in entrevistas if e.get("estado") == "agendada")
    reclutadores_activos   = sum(1 for r in reclutadores if r.get("activo") is True)
    candidatos_listo       = sum(1 for c in candidatos if c.get("estado") == "listo_entrevista")

    r2c1, r2c2, r2c3 = st.columns(3)
    r2c1.metric("Entrevistas agendadas", entrevistas_agendadas)
    r2c2.metric("Reclutadores activos",  reclutadores_activos)
    r2c3.metric("Candidatos listo entrevista", candidatos_listo)

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

    st.divider()
    st.subheader("Fábrica — Estado Global")
    with st.spinner("Cargando stats…"):
        _fs = _run_skill("factory_stats", {"dry_run": False}, source="eval")
    if _fs.get("ok"):
        _fsd = _fs.get("data", {})
        _sk  = _fsd.get("skills", {})
        _bo  = _fsd.get("bots", {})
        _ag  = _fsd.get("agents", {})
        fs1, fs2, fs3, fs4 = st.columns(4)
        fs1.metric("Skills totales",  _sk.get("total", 0),   f"{_sk.get('en_disco',0)} en disco")
        fs2.metric("Bots",            _bo.get("total", 0))
        fs3.metric("Agents",          _ag.get("total", 0))
        fs4.metric("Sincronizado",    "✅ Sí" if _sk.get("sincronizado") else "⚠️ No")
        _col_k, _col_v = st.columns(2)
        with _col_k:
            st.caption("Por tipo")
            st.json(_sk.get("por_tipo", {}), expanded=False)
        with _col_v:
            st.caption("Top verticales")
            st.json(_sk.get("top_verticales", {}), expanded=False)
    else:
        st.caption("factory_stats no disponible")


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
# Entrevistas
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Entrevistas":
    st.title("Entrevistas")

    entrevistas = _entrevistas()
    candidatos  = _candidatos()
    cands_map   = {c["id"]: c for c in candidatos}

    col_f1, col_f2 = st.columns(2)
    f_estado = col_f1.selectbox(
        "Estado",
        ["", "agendada", "cancelada", "realizada"],
        format_func=lambda x: "Todos" if not x else x,
    )
    f_buscar = col_f2.text_input("Buscar nombre de candidato")

    filtered = entrevistas
    if f_estado:
        filtered = [e for e in filtered if e.get("estado") == f_estado]
    if f_buscar:
        def _nombre_candidato(e: dict) -> str:
            cid  = e.get("candidato_id", "")
            cand = cands_map.get(cid, {})
            nombre_directo = e.get("nombre", "")
            return (cand.get("nombre") or nombre_directo or "").lower()
        filtered = [e for e in filtered if f_buscar.lower() in _nombre_candidato(e)]

    st.caption(f"{len(filtered)} entrevistas")

    import pandas as pd
    rows = []
    for e in filtered:
        cid  = e.get("candidato_id", "")
        cand = cands_map.get(cid, {})
        nombre = cand.get("nombre") or e.get("nombre", "—")
        folio_cand = _folio(cand, "C-") if cand else (cid[:6] + "..." if cid else "—")
        fecha_hora = e.get("fecha_hora") or e.get("fecha") or "—"
        if fecha_hora and fecha_hora != "—":
            fecha_hora = str(fecha_hora)[:16].replace("T", " ")
        rows.append({
            "Folio candidato": folio_cand,
            "Nombre":          nombre,
            "Reclutador ID":   e.get("reclutador_id", "—"),
            "Fecha/Hora":      fecha_hora,
            "Tipo":            e.get("tipo", "—"),
            "Estado":          _badge(e.get("estado", "—")),
            "Notas":           (e.get("notas") or "")[:80],
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Sin resultados")


# ═══════════════════════════════════════════════════════════════════════════════
# Reclutadores
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Reclutadores":
    st.title("Reclutadores")

    reclutadores = _reclutadores()

    st.caption(f"{len(reclutadores)} reclutadores")

    import pandas as pd
    rows = []
    for r in reclutadores:
        activo_val = r.get("activo")
        activo_str = "✅" if activo_val is True else "❌"
        rows.append({
            "Nombre":     r.get("nombre", "—"),
            "Zona":       r.get("zona", "—"),
            "Empresa ID": r.get("empresa_id", "—"),
            "Activo":     activo_str,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Sin reclutadores registrados")


# ═══════════════════════════════════════════════════════════════════════════════
# Seeds
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Seeds":
    st.title("Seeds de prueba")

    if st.button("＋ Crear Seed (1 vacante + 5 candidatos)", key="btn_seed1"):
        with st.spinner("Generando... puede tardar ~30s"):
            r = _run_skill("rh_seed_generator", {
                "empresa_id": _EMPRESA_ID,
                "n_vacantes": 1,
                "n_candidatos_por_vacante": 5,
                "profundidad": "simple",
                "dry_run": False,
                "tipo": "seed",
            })
        if r.get("ok"):
            st.success("Seed creado.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(r.get("error", "Error al crear seed"))

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


# ═══════════════════════════════════════════════════════════════════════════════
# Ultima Vacante
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Ultima Vacante":
    st.title("Ultima Vacante")

    # Boton pequeno de recarga
    if st.button("↺ Recargar", key="recargar_ultima_vacante"):
        st.cache_data.clear()
        st.rerun()

    lista_uv = _ultima_vacante()

    if not lista_uv:
        st.info("No hay vacantes registradas")
    else:
        vac = lista_uv[0]
        vid = vac.get("id", "")

        # ── Card superior ────────────────────────────────────────────────────
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**Folio:** {_folio(vac, 'V-')}")
                st.markdown(f"**Titulo:** {vac.get('titulo', '—')}")
                st.markdown(f"**Estado:** {_badge(vac.get('estado', '—'))}")
                st.markdown(f"**Turno:** {vac.get('turno') or '—'}")

            with col2:
                st.markdown(f"**Canal:** {vac.get('canal', '—')}")
                st.markdown(f"**Empresa ID:** {vac.get('empresa_id', '—')}")
                st.markdown(f"**Zona:** {vac.get('zona') or '—'}")

            with col3:
                st.markdown(f"**Tipo:** {vac.get('tipo', 'real')}")
                st.markdown(f"**Fecha creacion:** {(vac.get('created_at') or '')[:10]}")
                st.markdown(f"**Sueldo:** {vac.get('sueldo') or '—'}")

            if vac.get("descripcion"):
                with st.expander("Ver descripcion"):
                    st.write(vac["descripcion"])

            requisitos = vac.get("requisitos")
            if requisitos:
                with st.expander("Ver requisitos"):
                    if isinstance(requisitos, dict):
                        for k, v in requisitos.items():
                            st.markdown(f"**{k}:** {v}")
                    else:
                        st.write(requisitos)

        st.divider()

        if st.button("＋ Agregar 10 candidatos a esta vacante", key="btn_seedc10"):
            with st.spinner("Generando 10 candidatos... puede tardar ~45s"):
                r = _run_skill("rh_seed_generator", {
                    "empresa_id":           _EMPRESA_ID,
                    "vacante_id_existente": vid,
                    "vacante_titulo":       vac.get("titulo", ""),
                    "turno":               vac.get("turno", ""),
                    "zona":                vac.get("zona", ""),
                    "sueldo":              vac.get("sueldo", ""),
                    "n_vacantes":          0,
                    "n_candidatos_por_vacante": 10,
                    "profundidad":         "medio",
                    "dry_run":             False,
                    "tipo":                "seed",
                })
            if r.get("ok"):
                st.success("10 candidatos agregados.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(r.get("error", "Error al generar candidatos"))

        # ── Cuatro tabs ──────────────────────────────────────────────────────
        tab_cands, tab_pipe, tab_ai, tab_resp = st.tabs(
            ["Candidatos", "Pipeline", "Analisis AI", "Respuestas"]
        )

        # ── Tab Candidatos ───────────────────────────────────────────────────
        with tab_cands:
            import pandas as pd

            cands_vac  = _candidatos_vacante(vid)
            scores_vac = _scores_vacante(vid)
            scores_map_vac = {s.get("candidato_id"): s for s in scores_vac}

            if not cands_vac:
                st.info("Sin candidatos para esta vacante")
            else:
                rows = []
                for c in cands_vac:
                    sc = scores_map_vac.get(c.get("id"), {})
                    rows.append({
                        "Folio":      _folio(c, "C-"),
                        "Nombre":     c.get("nombre", "—"),
                        "Telefono":   c.get("telefono", "—"),
                        "Canal":      c.get("canal", "—"),
                        "Estado":     c.get("estado", "—"),
                        "Score":      sc.get("score_total", "—"),
                        "Pasa KO":    "✓" if sc.get("pasa_knockout") else "✗",
                        "Creado":     (c.get("created_at") or "")[:10],
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── Tab Pipeline ─────────────────────────────────────────────────────
        with tab_pipe:
            import pandas as pd

            pipeline_vac = _pipeline_vacante(vid)
            cands_vac_pl = _candidatos_vacante(vid)
            cands_map_pl = {c.get("id"): c for c in cands_vac_pl}

            if not pipeline_vac:
                st.info("Sin entradas de pipeline para esta vacante")
            else:
                rows = []
                for p in pipeline_vac:
                    cand = cands_map_pl.get(p.get("candidato_id"), {})
                    rows.append({
                        "Candidato": _folio(cand, "C-"),
                        "Nombre":    cand.get("nombre", "—"),
                        "Etapa":     _badge(p.get("etapa", "—")),
                        "Notas":     (p.get("notas") or "")[:80],
                        "Fecha":     (p.get("created_at") or "")[:10],
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── Tab Analisis AI ──────────────────────────────────────────────────
        with tab_ai:
            scores_ai  = _scores_vacante(vid)
            cands_ai   = _candidatos_vacante(vid)
            cands_map_ai = {c.get("id"): c for c in cands_ai}

            hay_analisis = False

            for sc in scores_ai:
                detalle = sc.get("detalle")
                if not detalle:
                    continue
                if not isinstance(detalle, dict):
                    continue
                if not detalle:
                    continue

                hay_analisis = True
                cid  = sc.get("candidato_id", "")
                cand = cands_map_ai.get(cid, {})
                nombre_cand = cand.get("nombre") or _folio(cand, "C-") or cid[:8]

                st.subheader(f"🧠 {nombre_cand}")

                for dim_key, dim_val in detalle.items():
                    if not isinstance(dim_val, dict):
                        st.markdown(f"**{dim_key}:** {dim_val}")
                        continue

                    st.markdown(f"**{dim_key}**")

                    recomendacion = (
                        dim_val.get("recomendacion") or ""
                    ).lower()

                    contenido_lines = []

                    score_val = dim_val.get("score") or dim_val.get("score_retencion")
                    if score_val is not None:
                        contenido_lines.append(f"- **Score:** {score_val}")

                    nivel_val = dim_val.get("nivel") or dim_val.get("riesgo")
                    if nivel_val is not None:
                        contenido_lines.append(f"- **Nivel/Riesgo:** {nivel_val}")

                    if dim_val.get("recomendacion"):
                        contenido_lines.append(f"- **Recomendacion:** {dim_val['recomendacion']}")

                    if dim_val.get("resumen"):
                        contenido_lines.append(f"- **Resumen:** {dim_val['resumen']}")

                    senales = dim_val.get("senales")
                    if senales and isinstance(senales, list) and len(senales) > 0:
                        contenido_lines.append("- **Señales:**")
                        for s_item in senales:
                            contenido_lines.append(f"  - {s_item}")

                    contenido_str = "\n".join(contenido_lines) if contenido_lines else str(dim_val)

                    if "contratar" in recomendacion:
                        st.success(contenido_str)
                    elif "revisar" in recomendacion:
                        st.warning(contenido_str)
                    elif "descartar" in recomendacion:
                        st.error(contenido_str)
                    else:
                        st.info(contenido_str)

                st.divider()

            if not hay_analisis:
                st.info("Sin analisis AI para esta vacante")

        # ── Tab Respuestas ───────────────────────────────────────────────────
        with tab_resp:
            import pandas as pd

            respuestas_vac = _respuestas_vacante(vid)
            cands_resp     = _candidatos_vacante(vid)
            scores_resp    = _scores_vacante(vid)
            cands_map_resp = {c.get("id"): c for c in cands_resp}
            scores_map_resp = {s.get("candidato_id"): s for s in scores_resp}

            if not respuestas_vac:
                st.info("Sin respuestas para esta vacante")
            else:
                # Pivot: una fila por candidato, una columna por pregunta
                by_cand: dict[str, dict] = {}
                preguntas_ord: list[str] = []
                seen_pregs: set[str] = set()

                for r in sorted(respuestas_vac, key=lambda x: x.get("orden", 0)):
                    cid  = r.get("candidato_id", "")
                    preg = r.get("pregunta") or f"P{r.get('orden','')}"
                    resp = r.get("respuesta") or "—"
                    if cid not in by_cand:
                        cand = cands_map_resp.get(cid, {})
                        sc   = scores_map_resp.get(cid, {})
                        by_cand[cid] = {
                            "Folio":  _folio(cand, "C-"),
                            "Nombre": cand.get("nombre") or "—",
                            "Estado": cand.get("estado") or "—",
                            "Score":  sc.get("score_total", "—"),
                            "KO":     "✓" if sc.get("pasa_knockout") else "✗",
                        }
                    by_cand[cid][preg] = resp
                    if preg not in seen_pregs:
                        seen_pregs.add(preg)
                        preguntas_ord.append(preg)

                cols_base = ["Folio", "Nombre", "Estado", "Score", "KO"]
                rows = [
                    {**{c: d.get(c, "—") for c in cols_base}, **{p: d.get(p, "—") for p in preguntas_ord}}
                    for d in by_cand.values()
                ]
                df = pd.DataFrame(rows, columns=cols_base + preguntas_ord)
                st.caption(f"{len(df)} candidatos · {len(preguntas_ord)} preguntas")
                st.dataframe(df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Análisis IA
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Análisis IA":
    import pandas as pd

    st.title("Análisis IA")

    if "analisis_resultados" not in st.session_state:
        st.session_state.analisis_resultados = {}

    scores_all  = _scores_full()
    candidatos  = _candidatos()
    vacantes    = _vacantes()
    cands_map   = {c["id"]: c for c in candidatos}
    vacs_map    = {v["id"]: v for v in vacantes}

    # ── Tabla resumen ────────────────────────────────────────────────────────
    st.subheader("Resumen de candidatos")
    rows = []
    for sc in scores_all:
        cid     = sc.get("candidato_id", "")
        cand    = cands_map.get(cid, {})
        vac     = vacs_map.get(cand.get("vacante_id", ""), {})
        detalle = sc.get("detalle") or {}
        sz      = detalle.get("shift_zone", {})
        comp    = detalle.get("dimension_compromiso", {})
        cond    = detalle.get("dimension_conducta", {})
        rows.append({
            "Folio":      _folio(cand, "C-"),
            "Nombre":     cand.get("nombre", "—"),
            "Vacante":    _folio(vac, "V-"),
            "Score":      sc.get("score_total", "—"),
            "KO":         "✓" if sc.get("pasa_knockout") else "✗",
            "Turno/Zona": sz.get("recomendacion", "—"),
            "Compromiso": f"{comp.get('score','—')} {comp.get('nivel','')}".strip(),
            "Conducta":   f"{cond.get('score','—')} {cond.get('nivel','')}".strip(),
            "Resumen SZ": (sz.get("resumen") or "")[:80],
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos. Corre un seed para generar candidatos con análisis.")

    st.divider()

    # ── Analizar todos los que no tienen análisis ─────────────────────────────
    sin_analisis = [sc for sc in scores_all if not (sc.get("detalle") or {}).get("shift_zone") and not (sc.get("detalle") or {}).get("dimension_compromiso")]
    if sin_analisis:
        st.caption(f"{len(sin_analisis)} candidatos sin análisis IA")
        if st.button(f"⚡ Analizar TODOS los candidatos sin análisis ({len(sin_analisis)})", key="btn_analizar_todos"):
            prog = st.progress(0, text="Iniciando...")
            for i, sc in enumerate(sin_analisis):
                cid  = sc.get("candidato_id", "")
                cand = cands_map.get(cid, {})
                vac  = vacs_map.get(cand.get("vacante_id", ""), {})
                prog.progress((i) / len(sin_analisis), text=f"Analizando {_folio(cand,'C-')} ({i+1}/{len(sin_analisis)})...")
                resultado = {}
                if vac.get("turno") or vac.get("zona"):
                    r = _run_skill("rh_shift_zone_validator", {
                        "turno_requerido": vac.get("turno", "no especificado"),
                        "zona_trabajo":    vac.get("zona", "no especificada"),
                        "candidato_id":    cid,
                    })
                    if r.get("ok"):
                        resultado["shift_zone"] = r["data"]
                for dim in ("compromiso", "conducta"):
                    r = _run_skill("rh_dimension_analyzer", {
                        "dimension":    dim,
                        "candidato_id": cid,
                        "puesto":       vac.get("titulo", "operador"),
                    })
                    if r.get("ok"):
                        resultado[f"dimension_{dim}"] = r["data"]
                st.session_state.analisis_resultados[cid] = resultado
            prog.progress(1.0, text="Completado.")
            st.cache_data.clear()
            st.rerun()

    # ── Análisis completo por candidato ──────────────────────────────────────
    st.subheader("Análisis completo por candidato")
    opciones = {c["id"]: f"{_folio(c,'C-')} — {c.get('nombre','')}" for c in candidatos}
    sel_id = st.selectbox("Selecciona candidato", [""] + list(opciones.keys()),
                          format_func=lambda x: opciones.get(x, "Selecciona...") if x else "Selecciona...")

    if sel_id:
        cand_sel = cands_map.get(sel_id, {})
        vac_sel  = vacs_map.get(cand_sel.get("vacante_id", ""), {})

        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            if st.button("⚡ Analizar todas las dimensiones", key="btn_analizar"):
                with st.spinner("Analizando 6 dimensiones + turno/zona (~30s)..."):
                    resultado = {}
                    # Shift zone
                    if vac_sel.get("turno") or vac_sel.get("zona"):
                        r = _run_skill("rh_shift_zone_validator", {
                            "turno_requerido": vac_sel.get("turno", "no especificado"),
                            "zona_trabajo":    vac_sel.get("zona", "no especificada"),
                            "candidato_id":    sel_id,
                        })
                        if r.get("ok"):
                            resultado["shift_zone"] = r["data"]
                    # 6 dimensiones
                    for dim in ("conducta", "fisico", "compromiso", "maquinaria", "rutas", "tecnico"):
                        r = _run_skill("rh_dimension_analyzer", {
                            "dimension":    dim,
                            "candidato_id": sel_id,
                            "puesto":       vac_sel.get("titulo", "operador"),
                        })
                        if r.get("ok"):
                            resultado[f"dimension_{dim}"] = r["data"]
                    st.session_state.analisis_resultados[sel_id] = resultado
                st.success("Análisis completado.")

        with col_info:
            st.write(f"**Puesto:** {vac_sel.get('titulo','—')} | **Turno:** {vac_sel.get('turno','—')} | **Zona:** {vac_sel.get('zona','—')}")

        res = st.session_state.analisis_resultados.get(sel_id)
        if res:
            sz = res.get("shift_zone")
            if sz:
                rec = sz.get("recomendacion", "")
                fn  = st.success if rec == "contratar" else (st.warning if rec == "revisar" else st.error)
                fn(f"**Turno/Zona:** {rec.upper()} — {sz.get('resumen','')}")

            dim_rows = []
            for key, val in res.items():
                if key.startswith("dimension_"):
                    dim_rows.append({
                        "Dimensión":     val.get("dimension", key).upper(),
                        "Score (1-10)":  val.get("score", "—"),
                        "Nivel":         val.get("nivel", "—"),
                        "Recomendación": val.get("recomendacion", "—"),
                        "Resumen":       (val.get("resumen") or "")[:100],
                    })
            if dim_rows:
                st.dataframe(pd.DataFrame(dim_rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Offer Builder
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Offer Builder":
    import pandas as pd

    st.title("Offer Builder")

    if "ofertas" not in st.session_state:
        st.session_state.ofertas = {}

    score_min = st.number_input("Score mínimo de candidatos", min_value=0, max_value=100, value=60, step=5)

    vacantes   = _vacantes()
    scores_all = _scores_full()
    candidatos = _candidatos()

    scores_map  = {s["candidato_id"]: s for s in scores_all}
    cands_map   = {c["id"]: c for c in candidatos}

    by_vac: dict[str, list] = {}
    for c in candidatos:
        vid = c.get("vacante_id", "")
        if vid not in by_vac:
            by_vac[vid] = []
        by_vac[vid].append(c)

    hay_vacantes = False
    for vac in vacantes:
        vid   = vac.get("id", "")
        cands = by_vac.get(vid, [])
        aptos = [c for c in cands
                 if (scores_map.get(c.get("id", ""), {}).get("score_total") or 0) >= score_min]
        if not aptos:
            continue
        hay_vacantes = True

        with st.expander(f"**{_folio(vac,'V-')}** — {vac.get('titulo','')}  |  {len(aptos)} candidatos ≥{score_min}pts"):
            st.caption(f"Zona: {vac.get('zona','—')} | Turno: {vac.get('turno','—')} | Sueldo: {vac.get('sueldo','—')}")
            for c in aptos:
                sc    = scores_map.get(c.get("id",""), {})
                cid   = c.get("id","")
                folio = _folio(c, "C-")
                col1, col2, col3 = st.columns([3, 1, 2])
                col1.write(f"**{folio}** — {c.get('nombre','—')}")
                col2.metric("Score", sc.get("score_total","—"))
                with col3:
                    if st.button("📄 Generar Oferta", key=f"offer_{cid}"):
                        with st.spinner("Generando oferta con IA..."):
                            r = _run_skill("rh_offer_builder", {
                                "puesto":         vac.get("titulo", ""),
                                "empresa":        _EMPRESA_ID,
                                "zona":           vac.get("zona", ""),
                                "notas_extra":    f"Candidato: {c.get('nombre','')}. Sueldo ofrecido: {vac.get('sueldo','')}",
                            })
                        if r.get("ok"):
                            st.session_state.ofertas[cid] = r["data"].get("texto_oferta", "")
                        else:
                            st.error(r.get("error", "Error"))
                if cid in st.session_state.ofertas:
                    st.text_area("Oferta generada", st.session_state.ofertas[cid],
                                 height=150, key=f"ta_{cid}")


# ═══════════════════════════════════════════════════════════════════════════════
# FB Groups Discovery
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "FB Groups":
    import pandas as pd

    st.title("FB Groups Discovery")

    if "fb_last_grupos" not in st.session_state:
        st.session_state.fb_last_grupos  = []
        st.session_state.fb_last_sid     = ""
        st.session_state.fb_last_fuente  = ""
        st.session_state.fb_last_tema    = ""

    tab_buscar, tab_historial = st.tabs(["Nueva búsqueda", "Historial"])

    # ── Nueva búsqueda ────────────────────────────────────────────────────────
    with tab_buscar:
        tema = st.text_input(
            "Tema de búsqueda",
            placeholder="operadores de tráiler Mérida · cemento México · maquinaria pesada Chiapas",
        )
        col_l, col_m = st.columns(2)
        with col_l:
            limite = st.select_slider("Cantidad de grupos", options=[10, 25, 50, 100], value=25)
        with col_m:
            min_miembros = st.select_slider("Miembros mínimos", options=[0, 100, 200, 500, 1000, 5000], value=100)
        if st.button("Buscar grupos", type="primary", disabled=not tema.strip()):
            with st.spinner("Buscando grupos en Facebook..."):
                engine_r = _run_skill("vertical_fb/fb_groupsearch_engine", {
                    "tema_busqueda": tema.strip(),
                    "limite":        limite,
                    "min_miembros":  min_miembros,
                    "dry_run":       False,
                })
            if not engine_r.get("ok"):
                st.error(f"Error en búsqueda: {engine_r.get('error', 'desconocido')}")
            else:
                ed     = engine_r.get("data") or {}
                grupos = ed.get("grupos", [])
                fuente = ed.get("fuente", "ia_sugerido")
                with st.spinner("Guardando resultados..."):
                    saver_r = _run_skill("vertical_fb/fb_groupsearch_saver", {
                        "grupos":        grupos,
                        "fuente":        fuente,
                        "tema_busqueda": tema.strip(),
                        "empresa_id":    _EMPRESA_ID,
                        "dry_run":       False,
                    })
                if not saver_r.get("ok"):
                    st.error(f"Error al guardar: {saver_r.get('error', 'desconocido')}")
                else:
                    sd = saver_r.get("data") or {}
                    st.session_state.fb_last_grupos = grupos
                    st.session_state.fb_last_sid    = sd.get("search_id", "")
                    st.session_state.fb_last_fuente = fuente
                    st.session_state.fb_last_tema   = tema.strip()

        if st.session_state.fb_last_sid:
            fuente_lbl = "Meta API" if st.session_state.fb_last_fuente == "meta_api" else "IA sugerido ⚠️"
            st.success(
                f"**{len(st.session_state.fb_last_grupos)} grupos** encontrados — "
                f"`{st.session_state.fb_last_sid}` — {fuente_lbl}"
            )
            df_new = pd.DataFrame([{
                "Nombre":      g.get("grupo_nombre", ""),
                "Miembros":    g.get("miembros_estimados", ""),
                "Ubicación":   g.get("ubicacion_detectada", ""),
                "Descripción": (g.get("descripcion") or "")[:80],
                "URL":         g.get("grupo_url", ""),
            } for g in st.session_state.fb_last_grupos])
            st.dataframe(df_new, use_container_width=True, hide_index=True)

    # ── Historial ─────────────────────────────────────────────────────────────
    with tab_historial:
        searches = select("fb_gs_searches", "select=*&order=created_at.desc&limit=200")

        if not searches:
            st.info("Sin búsquedas guardadas. Usa la pestaña Nueva búsqueda.")
        else:
            df_s = pd.DataFrame([{
                "Search ID": s.get("search_id", ""),
                "Tema":      s.get("tema_busqueda", ""),
                "Grupos":    s.get("total_grupos", 0),
                "Fuente":    s.get("fuente", ""),
                "Estado":    s.get("estado", ""),
                "Fecha":     (s.get("created_at") or "")[:10],
            } for s in searches])
            st.dataframe(df_s, use_container_width=True, hide_index=True)

            selected_id = st.selectbox(
                "Ver grupos de búsqueda",
                options=[s.get("search_id") for s in searches],
            )
            col1, col2 = st.columns([1, 5])
            with col1:
                ver = st.button("Ver grupos")
            with col2:
                borrar = st.button("Borrar búsqueda", type="secondary")

            if ver:
                grupos_h = select("fb_gs_groups", f"select=*&search_id=eq.{selected_id}&order=created_at.desc&limit=500")
                if not grupos_h:
                    st.info("Sin grupos para esta búsqueda.")
                else:
                    df_g = pd.DataFrame([{
                        "Nombre":      g.get("grupo_nombre", ""),
                        "Miembros":    g.get("miembros_estimados", ""),
                        "Ubicación":   g.get("ubicacion_detectada", ""),
                        "Descripción": (g.get("descripcion") or "")[:80],
                        "URL":         g.get("grupo_url", ""),
                        "Fuente":      g.get("fuente", ""),
                    } for g in grupos_h])
                    st.dataframe(df_g, use_container_width=True, hide_index=True)

            if borrar:
                del_r = _run_skill("vertical_fb/fb_groupsearch_delete", {"search_id": selected_id, "dry_run": False})
                if del_r.get("ok"):
                    st.success(f"{selected_id} eliminada.")
                else:
                    st.error(del_r.get("error", "Error al borrar"))


# ═══════════════════════════════════════════════════════════════════════════════
# Tasks — cola factory_tasks
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Tasks":
    import pandas as pd
    import json as _json_t
    from pathlib import Path as _Path_t

    st.title("Tasks — Cola de ejecución")

    # ── Roadmap / Features pendientes ─────────────────────────────────────────
    _roadmap_file = _Path_t(__file__).parent / "roadmap.json"
    _SEMAFORO = {"pendiente": "🟡", "en_curso": "🔵", "listo": "🟢", "bloqueado": "🔴"}

    with st.expander("📋 Roadmap — Features pendientes", expanded=True):
        _roadmap = []
        if _roadmap_file.exists():
            try:
                _roadmap = _json_t.loads(_roadmap_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if _roadmap:
            for _t in _roadmap:
                _sem = _SEMAFORO.get(_t.get("status", "pendiente"), "⚫")
                with st.container(border=True):
                    _hcol1, _hcol2 = st.columns([8, 1])
                    _hcol1.markdown(f"**#{_t['id']} — {_t['titulo']}**")
                    _hcol2.caption(f"{_sem} {_t.get('status','')}")
                    st.caption(_t.get("descripcion", ""))
                    _meta1, _meta2, _meta3 = st.columns(3)
                    _meta1.caption(f"Categoría: `{_t.get('categoria','')}`  |  Prioridad: {_t.get('prioridad','')}")
                    if _t.get("skills_a_construir"):
                        _meta2.caption("Skills: " + " · ".join(f"`{s}`" for s in _t["skills_a_construir"]))
                    if _t.get("requiere_creds"):
                        _meta3.caption("Creds: " + " · ".join(f"`{c}`" for c in _t["requiere_creds"]))
        else:
            st.info("Sin items en roadmap.json")

    st.divider()

    STATUS_COLORS = {
        "pendiente":  "🟡",
        "corriendo":  "🔵",
        "completada": "🟢",
        "error":      "🔴",
    }

    # ── Conteo resumen ────────────────────────────────────────────────────────
    all_tasks = select("factory_tasks",
        "select=task_id,skill_name,skill_source,status,prioridad,empresa_id,"
        "latencia_ms,costo_tokens,error_msg,created_at,started_at,finished_at,"
        "parent_task_id,generated_by,created_by"
        "&order=created_at.desc&limit=200"
    )

    conteo = {}
    for t in all_tasks:
        s = t.get("status", "?")
        conteo[s] = conteo.get(s, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pendientes",  conteo.get("pendiente",  0), delta=None)
    c2.metric("Corriendo",   conteo.get("corriendo",  0), delta=None)
    c3.metric("Completadas", conteo.get("completada", 0), delta=None)
    c4.metric("Errores",     conteo.get("error",      0), delta=None)

    st.divider()

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    f_status = col_f1.selectbox("Status", ["", "pendiente", "corriendo", "completada", "error"],
                                 format_func=lambda x: "Todos" if not x else x)
    f_source = col_f2.selectbox("Fuente", ["", "internos", "meta", "eval"],
                                 format_func=lambda x: "Todas" if not x else x)
    f_skill  = col_f3.text_input("Skill contiene", placeholder="ej: rh_dimension")

    tareas = all_tasks
    if f_status:
        tareas = [t for t in tareas if t.get("status") == f_status]
    if f_source:
        tareas = [t for t in tareas if t.get("skill_source") == f_source]
    if f_skill:
        tareas = [t for t in tareas if f_skill.lower() in (t.get("skill_name") or "").lower()]

    st.caption(f"{len(tareas)} tareas")

    # ── Tabla ─────────────────────────────────────────────────────────────────
    if tareas:
        rows = []
        for t in tareas:
            rows.append({
                "ID":        t.get("task_id", ""),
                "Skill":     t.get("skill_name", ""),
                "Fuente":    t.get("skill_source", "internos"),
                "Status":    STATUS_COLORS.get(t.get("status",""), "⚪") + " " + (t.get("status") or ""),
                "Prior.":    t.get("prioridad", 5),
                "ms":        t.get("latencia_ms", 0),
                "Tokens":    t.get("costo_tokens", 0),
                "Error":     (t.get("error_msg") or "")[:60],
                "Padre":     t.get("parent_task_id") or "",
                "Creado por": t.get("created_by") or "",
                "Creado":    (t.get("created_at") or "")[:16],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Sin tareas. Encola trabajo desde cualquier skill usando meta_task_enqueue.")

    # ── Encolar análisis de dimensiones ──────────────────────────────────────
    st.divider()
    st.subheader("Encolar análisis de dimensiones")

    emp_id_tasks = st.text_input("empresa_id", value="RH1", key="tasks_emp")
    col_b1, col_b2 = st.columns(2)

    if col_b1.button("Encolar dimensiones faltantes", key="btn_encolar_dims"):
        scores_r = select("scores",
            f"select=candidato_id,vacante_id,detalle&limit=500"
        )
        sin_analisis = [
            s for s in scores_r
            if not (s.get("detalle") or {}).get("dimension_compromiso")
        ]
        if not sin_analisis:
            st.info("Todos los candidatos ya tienen análisis de dimensiones.")
        else:
            tareas_enc = []
            dimensiones = ["conducta", "fisico", "compromiso", "maquinaria", "rutas", "tecnico"]
            for sc in sin_analisis[:10]:  # max 10 candidatos por vez
                for dim in dimensiones:
                    tareas_enc.append({
                        "skill_name":   "rh_dimension_analyzer",
                        "skill_source": "internos",
                        "context": {
                            "dimension":    dim,
                            "candidato_id": sc["candidato_id"],
                            "vacante_id":   sc.get("vacante_id"),
                            "guardar":      True,
                            "dry_run":      False,
                        },
                        "empresa_id":  emp_id_tasks,
                        "created_by":  "dashboard",
                        "prioridad":   7,
                    })
            r = _run_skill("meta_task_enqueue", {
                "tareas":     tareas_enc,
                "empresa_id": emp_id_tasks,
                "dry_run":    False,
            }, source="meta")
            if r.get("ok"):
                enc = r.get("data", {}).get("encoladas", [])
                st.success(f"{len(enc)} tareas encoladas para {len(sin_analisis[:100])} candidatos.")
            else:
                st.error(r.get("error", "Error al encolar"))

    if col_b2.button("Procesar cola (batch 20)", key="btn_run_tasks"):
        with st.spinner("Procesando tareas..."):
            r = _run_skill("meta_task_runner", {
                "batch_size": 20,
                "empresa_id": emp_id_tasks,
                "dry_run":    False,
            }, source="meta")
        if r.get("ok"):
            st.success(r.get("message", "Procesado"))
            st.json(r.get("data", {}).get("resumen", {}))
        else:
            st.error(r.get("error", "Error al procesar"))


# ═══════════════════════════════════════════════════════════════════════════════
# Meta Skills — Fábrica de Skills
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Meta Skills":
    import json as _json
    from pathlib import Path as _Path

    st.title("Meta Skills — Fábrica de Skills")

    # Pipeline visual
    st.markdown("""
    <div style="background:#1a1a2e;border-radius:10px;padding:14px 20px;font-family:monospace;font-size:13px;color:#ccc;margin-bottom:16px">
    <b style="color:#a0c4ff">PIPELINE</b><br><br>
    📝 <b>proceso_texto</b><br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#90ee90">workflow_capture</span> &nbsp;→ pasos estructurados<br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#90ee90">pattern_extractor</span> &nbsp;→ patrones automatizables<br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#90ee90">skill_spec_generator</span> → spec técnica completa<br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#ffd700">skill_code_generator</span> → service.py + skill.py (Sonnet)<br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#ffd700">skill_cases_generator</span> → casos de prueba<br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#ff9999">skill_safety_eval</span> &nbsp;&nbsp;→ revisión seguridad<br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#ff9999">skill_quality_eval</span> &nbsp;→ score calidad<br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#a0c4ff">new_skill</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→ archivos en disco + registry<br>
    &nbsp;&nbsp;&nbsp;↓ <span style="color:#a0c4ff">github_push</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→ deploy automático<br>
    </div>
    """, unsafe_allow_html=True)

    tab_auto, tab_paso, tab_lista, tab_eval = st.tabs([
        "🚀 Add New Skill", "🔧 Paso a Paso", "📋 Mis Skills", "🔍 Eval"
    ])

    # ── Tab 1: Add New Skill (automático) ────────────────────────────────────
    with tab_auto:
        st.subheader("Construir skill desde un proceso")

        col_l, col_r = st.columns([2, 1])
        with col_l:
            ms_proceso  = st.text_area(
                "Describe el proceso a automatizar",
                placeholder="Ej: Cada semana descargo un CSV de ventas, lo filtro por región, calculo totales por vendedor y lo envío por email al gerente.",
                height=130,
                key="ms_proceso_txt",
            )
        with col_r:
            ms_vertical    = st.selectbox("Vertical", ["general", "rh", "ventas", "ops", "meta", "eval", "factory"], key="ms_vertical")
            ms_patron_ix   = st.number_input("Índice de patrón (0=primero automatizable)", min_value=0, max_value=10, value=0, key="ms_patron_ix")
            ms_dry         = st.checkbox("Solo spec (dry_run)", value=True, key="ms_dry")
            ms_push        = st.checkbox("Push a GitHub al final", value=False, key="ms_push")

        if st.button("🚀 Construir Skill", type="primary", key="btn_build_skill", use_container_width=True):
            if not ms_proceso.strip():
                st.warning("Describe el proceso primero.")
            else:
                with st.spinner("Ejecutando pipeline…"):
                    r = _run_skill("proceso_to_skill", {
                        "proceso":       ms_proceso.strip(),
                        "vertical":      ms_vertical,
                        "patron_index":  ms_patron_ix,
                        "push":          ms_push,
                        "dry_run":       ms_dry,
                    }, source="meta")

                if r.get("ok"):
                    st.success(r.get("message", "OK"))
                    data = r.get("data", {})

                    # Log de pasos
                    log = data.get("log", [])
                    if log:
                        with st.expander("📋 Log de pasos", expanded=False):
                            for paso in log:
                                icon = "✅" if paso.get("ok") else "❌"
                                st.markdown(f"{icon} **{paso['paso']}** — {paso.get('message','')}")

                    # Spec
                    spec = data.get("spec", {})
                    if spec:
                        with st.expander(f"📄 Spec: `{spec.get('skill_name','?')}`", expanded=True):
                            c1, c2 = st.columns(2)
                            c1.markdown(f"**Nombre:** `{spec.get('skill_name','')}`")
                            c1.markdown(f"**Vertical:** {spec.get('vertical','')}")
                            c1.markdown(f"**Requiere IA:** {'Sí' if spec.get('requiere_ia') else 'No'}")
                            c1.markdown(f"**Requiere DB:** {'Sí' if spec.get('requiere_db') else 'No'}")
                            c2.markdown(f"**Descripción:** {spec.get('descripcion','')}")
                            c2.markdown(f"**Env vars:** `{', '.join(spec.get('requires_env',[]))}`")
                            st.markdown("**Lógica principal:**")
                            st.info(spec.get("logica_principal", ""))
                            params = spec.get("context_params", [])
                            if params:
                                st.markdown("**Parámetros:**")
                                st.dataframe(params, use_container_width=True, hide_index=True)

                    # Código generado
                    codigo = data.get("codigo") or {}
                    svc = codigo.get("service_py", "")
                    if svc:
                        with st.expander("🐍 service.py generado", expanded=True):
                            st.code(svc, language="python")
                        skl = codigo.get("skill_py", "")
                        if skl:
                            with st.expander("🐍 skill.py", expanded=False):
                                st.code(skl, language="python")

                    # Casos de prueba
                    casos = data.get("casos_prueba", [])
                    if casos:
                        with st.expander(f"🧪 {len(casos)} casos de prueba", expanded=False):
                            import pandas as _pd
                            st.dataframe(_pd.DataFrame(casos), use_container_width=True, hide_index=True)

                else:
                    st.error(r.get("error", "Error desconocido"))
                    data = r.get("data", {})
                    if data.get("log"):
                        for paso in data["log"]:
                            icon = "✅" if paso.get("ok") else "❌"
                            st.markdown(f"{icon} **{paso['paso']}** — {paso.get('message','')}")

    # ── Tab 2: Paso a Paso ────────────────────────────────────────────────────
    with tab_paso:
        st.subheader("Ejecutar cada paso del pipeline manualmente")

        STEPS = [
            ("1. Capturar proceso",  "workflow_capture",     "meta"),
            ("2. Extraer patrones",  "pattern_extractor",    "meta"),
            ("3. Generar spec",      "skill_spec_generator", "meta"),
            ("4. Generar código",    "skill_code_generator", "meta"),
            ("5. Generar casos",     "skill_cases_generator","meta"),
            ("6. Eval seguridad",    "skill_safety_eval",    "eval"),
            ("7. Eval calidad",      "skill_quality_eval",   "eval"),
            ("8. Regression check",  "regression_eval",      "eval"),
        ]

        step_sel  = st.selectbox("Paso", [s[0] for s in STEPS], key="ms_step_sel")
        skill_sel = next(s for s in STEPS if s[0] == step_sel)
        skill_id  = skill_sel[1]
        skill_src = skill_sel[2]
        st.caption(f"Skill: `{skill_id}`  |  Fuente: `{skill_src}`")

        dry_paso = st.checkbox("dry_run", value=False, key="ms_dry_paso")
        ctx = None

        # helper: propaga output del paso anterior al campo de este paso
        def _prop_banner(from_skill: str, label: str, state_key: str, extract_fn):
            prev = st.session_state.get(f"ms_out_{from_skill}", {})
            val  = extract_fn(prev) if prev else None
            if val:
                if state_key not in st.session_state:
                    st.session_state[state_key] = val
                c1, c2 = st.columns([3, 1])
                c1.caption(f"← output de `{from_skill}` disponible")
                if c2.button("Usar", key=f"prop_{state_key}"):
                    st.session_state[state_key] = val
                    st.rerun()

        # ── inputs dedicados por paso ──────────────────────────────────────────
        if skill_id == "workflow_capture":
            p_proceso = st.text_area("Proceso a capturar", height=100,
                placeholder="Ej: Cada semana reviso candidatos nuevos y los puntuo a mano en Excel",
                key="pp_proceso")
            ctx = {"proceso": p_proceso}

        elif skill_id == "pattern_extractor":
            _prop_banner("workflow_capture", "pasos", "pp_pasos_pe",
                         lambda d: _json.dumps(d.get("pasos", []), indent=2, ensure_ascii=False))
            p_nombre = st.text_input("Nombre del proceso", value="mi_proceso", key="pp_nombre_pe")
            default_pasos = '[{"numero":1,"accion":"revisar lista","input":"candidatos","output":"seleccion","automatizable":true}]'
            if "pp_pasos_pe" not in st.session_state:
                st.session_state["pp_pasos_pe"] = default_pasos
            p_pasos = st.text_area("Pasos (JSON array)", height=120, key="pp_pasos_pe")
            try:
                ctx = {"pasos": _json.loads(p_pasos), "proceso_nombre": p_nombre}
            except Exception as e:
                st.error(f"Pasos JSON invalido: {e}")

        elif skill_id == "skill_spec_generator":
            _prop_banner("pattern_extractor", "patron", "pp_patron_sg",
                         lambda d: _json.dumps((d.get("patrones") or [{}])[0], indent=2, ensure_ascii=False))
            default_patron = '{"nombre":"revisar_candidatos","descripcion":"revisa y puntua candidatos","tipo":"repetitivo","automatizable":true}'
            if "pp_patron_sg" not in st.session_state:
                st.session_state["pp_patron_sg"] = default_patron
            p_patron  = st.text_area("Patron (JSON)", height=120, key="pp_patron_sg")
            p_ctx_pro = st.text_input("Contexto del proceso (opcional)", key="pp_ctx_pro")
            try:
                ctx = {"patron": _json.loads(p_patron), "proceso_contexto": p_ctx_pro}
            except Exception as e:
                st.error(f"Patron JSON invalido: {e}")

        elif skill_id == "skill_code_generator":
            _prop_banner("skill_spec_generator", "spec", "pp_spec_code",
                         lambda d: _json.dumps(d, indent=2, ensure_ascii=False))
            default_spec = '{"skill_name":"mi_skill","descripcion":"hace algo util","context_params":[],"output_fields":[],"logica_principal":"valida input, procesa, retorna resultado","requiere_ia":false,"requiere_db":false,"requires_env":[]}'
            if "pp_spec_code" not in st.session_state:
                st.session_state["pp_spec_code"] = default_spec
            p_spec = st.text_area("Spec (JSON)", height=180, key="pp_spec_code")
            try:
                ctx = {"spec": _json.loads(p_spec)}
            except Exception as e:
                st.error(f"Spec JSON invalido: {e}")

        elif skill_id == "skill_cases_generator":
            _prop_banner("skill_spec_generator", "spec", "pp_spec_cases",
                         lambda d: _json.dumps(d, indent=2, ensure_ascii=False))
            default_spec2 = '{"skill_name":"mi_skill","descripcion":"hace algo util","context_params":[],"output_fields":[],"casos_edge":[]}'
            if "pp_spec_cases" not in st.session_state:
                st.session_state["pp_spec_cases"] = default_spec2
            p_spec2   = st.text_area("Spec (JSON)", height=150, key="pp_spec_cases")
            p_n_casos = st.number_input("Numero de casos", min_value=1, max_value=10, value=5, key="pp_ncasos")
            try:
                ctx = {"spec": _json.loads(p_spec2), "n_casos": p_n_casos}
            except Exception as e:
                st.error(f"Spec JSON invalido: {e}")

        elif skill_id == "skill_safety_eval":
            p_sn  = st.text_input("Nombre del skill", value="rh_basic_validation", key="pp_safety_skill")
            p_src = st.selectbox("Fuente", ["internos", "meta", "eval"], key="pp_safety_src")
            ctx   = {"skill_name": p_sn, "source": p_src}

        elif skill_id == "skill_quality_eval":
            p_sn2  = st.text_input("Nombre del skill", value="rh_basic_validation", key="pp_quality_skill")
            p_src2 = st.selectbox("Fuente", ["internos", "meta", "eval"], key="pp_quality_src")
            p_inp  = st.text_area("test_input (JSON)", value='{"candidato_id":"test-dry"}', height=80, key="pp_quality_inp")
            try:
                ctx = {"skill_name": p_sn2, "source": p_src2, "test_input": _json.loads(p_inp)}
            except Exception as e:
                st.error(f"test_input JSON invalido: {e}")

        elif skill_id == "regression_eval":
            ctx = {}

        # Mostrar output del paso anterior si existe
        prev_key = f"ms_output_{skill_id}"
        if st.session_state.get(prev_key):
            with st.expander("📤 Output del último run", expanded=False):
                prev = st.session_state[prev_key]
                svc_prev = (prev.get("data") or {}).get("service_py", "")
                if svc_prev:
                    st.code(svc_prev, language="python")
                else:
                    st.json(prev.get("data", prev))

        if ctx is not None and st.button(f"▶ Ejecutar {skill_id}", key="btn_run_paso"):
            ctx["dry_run"] = dry_paso
            with st.spinner("Ejecutando…"):
                r = _run_skill(skill_id, ctx, source=skill_src)
            st.session_state[prev_key] = r
            # guardar data para propagación al paso siguiente
            st.session_state[f"ms_out_{skill_id}"] = r.get("data", {})
            if r.get("ok"):
                st.success(r.get("message", "OK"))
                data_r = r.get("data", {})
                # service_py como código, resto como JSON
                svc_out = data_r.get("service_py", "")
                if svc_out:
                    st.code(svc_out, language="python")
                    rest = {k: v for k, v in data_r.items() if k != "service_py"}
                    if rest:
                        st.json(rest)
                else:
                    st.json(data_r)
            else:
                st.error(r.get("error", "Error"))
                st.json(r)

    # ── Tab 3: Mis Skills ─────────────────────────────────────────────────────
    with tab_lista:
        st.subheader("Skills Meta y Eval registrados")

        _base_sk = _Path(__file__).parent.parent.parent / "factory" / "skills"

        def _listar_skills_dir(folder: str) -> list[dict]:
            d = _base_sk / folder
            if not d.exists():
                return []
            result = []
            for p in sorted(d.iterdir()):
                if not p.is_dir():
                    continue
                m = p / "manifest.json"
                if m.exists():
                    try:
                        info = _json.loads(m.read_text(encoding="utf-8"))
                    except Exception:
                        info = {}
                    result.append({
                        "Tipo":        folder,
                        "Nombre":      p.name,
                        "Descripción": info.get("description", ""),
                        "Env vars":    ", ".join(info.get("requires_env", [])),
                        "service.py":  "✅" if (p / "service.py").exists() else "❌",
                    })
            return result

        meta_skills = _listar_skills_dir("meta")
        eval_skills = _listar_skills_dir("eval")

        import pandas as _pd
        if meta_skills:
            st.markdown("**Meta Skills** (generación / orquestación)")
            st.dataframe(_pd.DataFrame(meta_skills), use_container_width=True, hide_index=True)
        if eval_skills:
            st.markdown("**Eval Skills** (verificación / calidad)")
            st.dataframe(_pd.DataFrame(eval_skills), use_container_width=True, hide_index=True)

        st.caption(f"{len(meta_skills)} meta · {len(eval_skills)} eval")

        st.divider()
        st.markdown("**Registry Sync** — agrega al registry los skills que faltan en disco")
        rs_dry = st.checkbox("dry_run (solo previsualizar)", value=True, key="rs_dry")
        if st.button("▶ Sincronizar Registry", key="btn_registry_sync"):
            with st.spinner("Escaneando…"):
                r = _run_skill("skill_registry_sync", {"dry_run": rs_dry}, source="meta")
            if r.get("ok"):
                d = r.get("data", {})
                if d.get("agregados", 0) == 0:
                    st.success("Registry sincronizado — nada que agregar")
                else:
                    if rs_dry:
                        st.info(r.get("message", ""))
                    else:
                        st.success(r.get("message", ""))
                detalle = d.get("detalle", [])
                if detalle:
                    st.dataframe(_pd.DataFrame(detalle), use_container_width=True, hide_index=True)
                st.caption(f"En disco: {d.get('total_disco',0)}  |  Ya existían: {d.get('ya_existen',0)}")
            else:
                st.error(r.get("error", "Error"))

    # ── Tab 4: Eval ───────────────────────────────────────────────────────────
    with tab_eval:
        st.subheader("Verificar skills existentes")

        # ── Fila 1: Regression + Health Check ────────────────────────────────
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            st.markdown("**Regression Eval** — corre skills core con dry_run")
            if st.button("▶ Correr Regression", key="btn_regression"):
                with st.spinner("Corriendo…"):
                    r = _run_skill("regression_eval", {"dry_run": False}, source="eval")
                if r.get("ok"):
                    d = r.get("data", {})
                    total  = d.get("total", 0)
                    ok_cnt = d.get("ok", 0)
                    errors = d.get("errores", 0)
                    st.metric("Resultado", f"{ok_cnt}/{total} OK", delta=f"-{errors} errores" if errors else None)
                    resultados = d.get("resultados", [])
                    if resultados:
                        st.dataframe(
                            _pd.DataFrame(resultados)[["skill", "pass", "latencia_ms", "error"]],
                            use_container_width=True, hide_index=True,
                        )
                else:
                    st.error(r.get("error", "Error"))

        with col_e2:
            st.markdown("**Health Check** — estado de todos los skills")
            solo_mal = st.checkbox("Solo con problemas", value=True, key="hc_solo_mal")
            if st.button("▶ Correr Health Check", key="btn_health"):
                with st.spinner("Escaneando…"):
                    r = _run_skill("skill_health_check", {"solo_problemas": solo_mal, "dry_run": False}, source="eval")
                if r.get("ok"):
                    d = r.get("data", {})
                    st.success(r.get("message", ""))
                    skills_r = d.get("skills", [])
                    if skills_r:
                        df_hc = _pd.DataFrame(skills_r)[["semaforo", "nombre", "folder", "en_registry", "service_py", "skill_py", "issues"]]
                        st.dataframe(df_hc, use_container_width=True, hide_index=True)
                    else:
                        st.info("Todos los skills están sanos.")
                else:
                    st.error(r.get("error", "Error"))

        st.divider()

        # ── Fila 2: Orphan Detector + Manifest Validator ──────────────────────
        col_e3, col_e4 = st.columns(2)

        with col_e3:
            st.markdown("**Orphan Detector** — huerfanos y fantasmas")
            if st.button("▶ Detectar Orphans", key="btn_orphan"):
                with st.spinner("Analizando…"):
                    r = _run_skill("skill_orphan_detector", {"dry_run": False}, source="eval")
                if r.get("ok"):
                    d = r.get("data", {})
                    if d.get("limpio"):
                        st.success("Fabrica limpia — sin huerfanos ni fantasmas")
                    else:
                        st.warning(r.get("message", ""))
                        problemas = d.get("problemas", [])
                        if problemas:
                            st.dataframe(_pd.DataFrame(problemas), use_container_width=True, hide_index=True)
                    st.caption(f"En disco: {d.get('total_disco',0)}  |  En registry: {d.get('total_registry',0)}")
                else:
                    st.error(r.get("error", "Error"))

        with col_e4:
            st.markdown("**Manifest Validator** — campos requeridos")
            mv_skill = st.text_input("Skill específico (vacío = todos)", value="", key="mv_skill")
            if st.button("▶ Validar Manifests", key="btn_manifest_val"):
                with st.spinner("Validando…"):
                    ctx_mv = {"dry_run": False}
                    if mv_skill.strip():
                        ctx_mv["skill_name"] = mv_skill.strip()
                    r = _run_skill("skill_manifest_validator", ctx_mv, source="eval")
                if r.get("ok"):
                    d = r.get("data", {})
                    if d.get("invalidos", 0) == 0:
                        st.success(r.get("message", "Todos válidos"))
                    else:
                        st.warning(r.get("message", ""))
                    resultados = d.get("resultados", [])
                    invalidos_r = [r2 for r2 in resultados if not r2.get("valido")]
                    if invalidos_r:
                        st.dataframe(_pd.DataFrame(invalidos_r), use_container_width=True, hide_index=True)
                else:
                    st.error(r.get("error", "Error"))

        st.divider()

        # ── Fila 3: Safety + Doc Generator ───────────────────────────────────
        col_e5, col_e6 = st.columns(2)

        with col_e5:
            st.markdown("**Safety Eval** — detecta patrones peligrosos")
            ev_skill  = st.text_input("Nombre del skill", value="rh_basic_validation", key="ev_skill_name")
            ev_source = st.selectbox("Fuente", ["internos", "meta", "eval"], key="ev_source")
            if st.button("▶ Revisar Seguridad", key="btn_safety"):
                with st.spinner("Analizando…"):
                    r = _run_skill("skill_safety_eval", {"skill_name": ev_skill, "source": ev_source}, source="eval")
                if r.get("ok"):
                    d = r.get("data", {})
                    if d.get("safe"):
                        st.success(f"SEGURO — score {d.get('score', 0):.0%}")
                    else:
                        st.warning(r.get("message", ""))
                    hallazgos = d.get("hallazgos", [])
                    if hallazgos:
                        st.dataframe(_pd.DataFrame(hallazgos), use_container_width=True, hide_index=True)
                    st.caption(f"dry_run: {'✅' if d.get('tiene_dry_run') else '❌'}  |  {d.get('lineas_revisadas', 0)} líneas")
                else:
                    st.error(r.get("error", "Error"))

        with col_e6:
            st.markdown("**Doc Generator** — genera markdown de un skill")
            dg_skill  = st.text_input("Nombre del skill", value="rh_basic_validation", key="dg_skill")
            dg_source = st.selectbox("Fuente", ["", "internos", "meta", "eval"],
                                      format_func=lambda x: "Auto-detectar" if not x else x, key="dg_source")
            if st.button("▶ Generar Docs", key="btn_doc_gen"):
                with st.spinner("Generando…"):
                    ctx_dg = {"skill_name": dg_skill, "dry_run": False}
                    if dg_source:
                        ctx_dg["source"] = dg_source
                    r = _run_skill("skill_doc_generator", ctx_dg, source="meta")
                if r.get("ok"):
                    md = r.get("data", {}).get("markdown", "")
                    st.markdown(md)
                else:
                    st.error(r.get("error", "Error"))

        st.divider()

        # ── Fila 4: Batch Eval + Import Checker ───────────────────────────────
        col_e7, col_e8 = st.columns(2)

        with col_e7:
            st.markdown("**Batch Eval** — health + orphan + manifest + regression en uno")
            if st.button("▶ Correr Batch Eval", key="btn_batch_eval"):
                with st.spinner("Evaluando fábrica completa…"):
                    r = _run_skill("skill_batch_eval", {"dry_run": False}, source="eval")
                if r.get("ok"):
                    d = r.get("data", {})
                    res = d.get("resumen", {})
                    st.success(r.get("message", "OK"))
                    b1, b2, b3, b4 = st.columns(4)
                    b1.metric("Skills OK",    res.get("skills_ok", 0))
                    b2.metric("Con error",    res.get("skills_con_error", 0))
                    b3.metric("Huérfanos",    res.get("huerfanos", 0) + res.get("fantasmas", 0))
                    b4.metric("Regression",   f"{res.get('regression_ok',0)}/{res.get('regression_total',0)}")
                    st.caption(f"Latencia total: {res.get('latencia_total_ms',0)} ms")
                    resultados = d.get("resultados", {})
                    if resultados:
                        with st.expander("Detalle por check", expanded=False):
                            for check_name, check_r in resultados.items():
                                icon = "✅" if check_r.get("ok") else "❌"
                                st.markdown(f"{icon} **{check_name}** — {check_r.get('message','')} ({check_r.get('ms',0)} ms)")
                else:
                    st.error(r.get("error", "Error"))

        with col_e8:
            st.markdown("**Import Checker** — verifica imports de un skill")
            ic_skill  = st.text_input("Nombre del skill", value="rh_basic_validation", key="ic_skill")
            ic_source = st.selectbox("Fuente", ["", "internos", "meta", "eval"],
                                      format_func=lambda x: "Auto-detectar" if not x else x, key="ic_source")
            if st.button("▶ Verificar Imports", key="btn_import_check"):
                with st.spinner("Analizando imports…"):
                    ctx_ic = {"skill_name": ic_skill, "dry_run": False}
                    if ic_source:
                        ctx_ic["source"] = ic_source
                    r = _run_skill("skill_import_checker", ctx_ic, source="eval")
                if r.get("ok"):
                    d = r.get("data", {})
                    if d.get("faltantes", 0) == 0:
                        st.success(r.get("message", "Todos los imports disponibles"))
                    else:
                        st.warning(r.get("message", ""))
                    imports_r = d.get("imports", [])
                    if imports_r:
                        st.dataframe(_pd.DataFrame(imports_r), use_container_width=True, hide_index=True)
                else:
                    st.error(r.get("error", "Error"))

        st.divider()

        # ── KPI Dashboard — meta_eval_kpis ────────────────────────────────────
        st.markdown("**KPI Pipeline Fábrica** — cobertura y estado de meta/eval skills")
        if st.button("▶ Cargar KPIs", key="btn_meta_kpis"):
            with st.spinner("Calculando KPIs…"):
                r = _run_skill("meta_eval_kpis", {"dry_run": False}, source="eval")
            if r.get("ok"):
                d = r.get("data", {})
                res = d.get("resumen", {})
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Meta skills",    res.get("total_meta", 0), f"{res.get('meta_completos',0)} completos")
                k2.metric("Eval skills",    res.get("total_eval", 0), f"{res.get('eval_completos',0)} completos")
                k3.metric("Pipeline cubierto", f"{res.get('cobertura_pipeline',0)}%")
                k4.metric("En registry",    res.get("meta_en_registry", 0) + res.get("eval_en_registry", 0))

                pip = d.get("pipeline", {})
                pc1, pc2 = st.columns(2)
                with pc1:
                    st.caption("Pipeline META")
                    for s in pip.get("meta", []):
                        st.markdown(f"{s['semaforo']} `{s['nombre']}` — {s['estado']}")
                with pc2:
                    st.caption("Pipeline EVAL")
                    for s in pip.get("eval", []):
                        st.markdown(f"{s['semaforo']} `{s['nombre']}` — {s['estado']}")
            else:
                st.error(r.get("error", "Error"))


# ═══════════════════════════════════════════════════════════════════════════════
# SAT — Facturas CFDI
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "SAT":
    import pandas as _pd_sat
    from datetime import datetime as _dt

    st.title("SAT — Facturas CFDI")

    _sat_rfc = os.getenv("SAT_RFC", "")
    _sat_ok  = bool(_sat_rfc and os.getenv("SAT_EFIRMA_CER_B64"))

    _h1, _h2, _h3 = st.columns(3)
    _h1.metric("RFC configurado", _sat_rfc or "no configurado")
    _h2.metric("e.firma", "Cargada" if _sat_ok else "Pendiente")
    _h3.metric("Credenciales SAT", "Listas" if _sat_ok else "Faltan env vars")

    if not _sat_ok:
        st.warning("Configura en Render: SAT_RFC, SAT_EFIRMA_CER_B64, SAT_EFIRMA_KEY_B64, SAT_EFIRMA_PASSWORD")

    st.divider()

    with st.expander("Convertir e.firma a base64", expanded=not _sat_ok):
        import base64 as _b64mod
        st.markdown("""
**¿Qué es esto?**
Para que el sistema pueda conectarse al SAT necesita tu **e.firma** (antes FIEL) — son dos archivos
que el SAT te entrega: `.cer` (certificado) y `.key` (llave privada). Como no podemos subir archivos
directamente a Render, los convertimos a texto base64 y los pegamos como variables de entorno.

**Pasos:**
1. Sube aquí tu `.cer` y tu `.key` → aparece el texto base64 de cada uno
2. Entra a **[render.com](https://render.com)** → tu servicio → **Environment**
3. Agrega o edita estas variables:

| Variable | Valor |
|---|---|
| `EMPRESA_ID` | El código de empresa (ej. `RH1`) |
| `SAT_RFC` | Tu RFC (ej. `XAXX010101000`) |
| `SAT_EFIRMA_CER_B64` | El texto que aparece abajo al subir el `.cer` |
| `SAT_EFIRMA_KEY_B64` | El texto que aparece abajo al subir el `.key` |
| `SAT_EFIRMA_PASSWORD` | La contraseña de tu e.firma |

4. Clic en **Save Changes** → Render redeploya automáticamente → listo
""")
        st.divider()
        st.caption("Sube tus archivos para generar el base64:")
        _ub1, _ub2 = st.columns(2)
        _cer_up = _ub1.file_uploader("Certificado (.cer)", key="sat_cer_up")
        _key_up = _ub2.file_uploader("Llave privada (.key)", key="sat_key_up")
        if _cer_up:
            _cer_b64_str = _b64mod.b64encode(_cer_up.read()).decode()
            _ub1.text_area("SAT_EFIRMA_CER_B64 — selecciona todo y copia:",
                           value=_cer_b64_str, height=130, key="sat_cer_b64_out")
            _ub1.caption("Ctrl+A dentro del campo para seleccionar todo")
        if _key_up:
            _key_b64_str = _b64mod.b64encode(_key_up.read()).decode()
            _ub2.text_area("SAT_EFIRMA_KEY_B64 — selecciona todo y copia:",
                           value=_key_b64_str, height=130, key="sat_key_b64_out")
            _ub2.caption("Ctrl+A dentro del campo para seleccionar todo")

    st.divider()

    with st.expander("Descargar CFDIs del SAT", expanded=not _sat_ok):
        _sc1, _sc2, _sc3 = st.columns(3)
        _s_fi   = _sc1.text_input("Fecha inicio (YYYY-MM-DD)",
                                   value=f"{_dt.now().year}-{_dt.now().month:02d}-01", key="sat_fi")
        _s_ff   = _sc2.text_input("Fecha fin (YYYY-MM-DD)",
                                   value=_dt.now().strftime("%Y-%m-%d"), key="sat_ff")
        _s_tipo = _sc3.selectbox("Tipo", ["E", "R", "Ambos"],
                                  format_func=lambda x: {"E": "Emitidos (ventas)",
                                                          "R": "Recibidos (gastos)",
                                                          "Ambos": "Ambos"}.get(x, x),
                                  key="sat_tipo")
        _s_tc = st.selectbox("Tipo comprobante (vacio=todos)",
                              ["", "I", "E", "T", "N", "P"],
                              format_func=lambda x: {"": "Todos", "I": "Ingreso", "E": "Egreso",
                                                      "T": "Traslado", "N": "Nomina", "P": "Pago"}.get(x, x),
                              key="sat_tc")
        if st.button("Sincronizar con SAT", type="primary", key="btn_sat_sync", disabled=not _sat_ok):
            _tipos_sync = ["E", "R"] if _s_tipo == "Ambos" else [_s_tipo]
            for _t in _tipos_sync:
                with st.spinner(f"Descargando {_t}..."):
                    _r = _run_skill("vertical_sat/sat_cfdi_sync", {
                        "fecha_inicio":     _s_fi,
                        "fecha_fin":        _s_ff,
                        "tipo":             _t,
                        "tipo_comprobante": _s_tc,
                        "dry_run":          False,
                    })
                if _r.get("ok"):
                    st.success(f"{_t}: {_r.get('message', 'OK')}")
                    for _l in _r.get("data", {}).get("log", []):
                        icon = "OK" if _l.get("ok") else "ERR"
                        st.caption(f"{icon} {_l['paso']} — {_l.get('msg', '')}")
                else:
                    st.error(f"{_t}: {_r.get('error', 'Error')}")

    st.divider()

    _mes_actual = _dt.now().strftime("%Y-%m")
    _fc1, _fc2, _fc3 = st.columns(3)
    _f_mes = _fc1.text_input("Mes (YYYY-MM)", value=_mes_actual, key="sat_f_mes")
    _f_dia = _fc2.text_input("Dia especifico YYYY-MM-DD (vacio=mes completo)", value="", key="sat_f_dia")
    _f_rfc = _fc3.text_input("RFC", value=_sat_rfc, key="sat_f_rfc")

    _ctx_list = {"rfc_propietario": _f_rfc, "dry_run": False}
    if _f_dia.strip():
        _ctx_list["dia"] = _f_dia.strip()
    elif _f_mes.strip():
        _ctx_list["mes"] = _f_mes.strip()

    st.subheader("CFDIs Emitidos (ventas)")
    with st.spinner("Cargando emitidos..."):
        _re = _run_skill("vertical_sat/sat_cfdi_list", {**_ctx_list, "tipo": "E"})
    if _re.get("ok"):
        _de = _re.get("data", {})
        _me1, _me2, _me3 = st.columns(3)
        _me1.metric("Total emitidos",  _de.get("total", 0))
        _me2.metric("Monto total",     "${:,.2f}".format(_de.get("monto_total", 0)))
        _me3.metric("Tipo Ingreso (I)", _de.get("total_ingresos", 0))
        _cfdis_e = _de.get("cfdis", [])
        if _cfdis_e:
            import pandas as _pd2
            _df_e   = _pd2.DataFrame(_cfdis_e)
            _cols_e = [c for c in ["fecha_emision", "uuid_cfdi", "rfc_receptor", "nombre_receptor",
                                    "tipo_comprobante", "total", "moneda", "forma_pago"]
                       if c in _df_e.columns]
            st.dataframe(_df_e[_cols_e], use_container_width=True, hide_index=True)
        else:
            st.info("Sin CFDIs emitidos para este periodo.")
    else:
        st.caption("sat_cfdi_list no disponible — " + _re.get("error", ""))

    st.divider()

    st.subheader("CFDIs Recibidos (gastos / compras)")
    with st.spinner("Cargando recibidos..."):
        _rr = _run_skill("vertical_sat/sat_cfdi_list", {**_ctx_list, "tipo": "R"})
    if _rr.get("ok"):
        _dr = _rr.get("data", {})
        _mr1, _mr2, _mr3 = st.columns(3)
        _mr1.metric("Total recibidos", _dr.get("total", 0))
        _mr2.metric("Monto total",     "${:,.2f}".format(_dr.get("monto_total", 0)))
        _mr3.metric("Tipo Egreso (E)", _dr.get("total_egresos", 0))
        _cfdis_r = _dr.get("cfdis", [])
        if _cfdis_r:
            import pandas as _pd3
            _df_r   = _pd3.DataFrame(_cfdis_r)
            _cols_r = [c for c in ["fecha_emision", "uuid_cfdi", "rfc_emisor", "nombre_emisor",
                                    "tipo_comprobante", "total", "moneda", "forma_pago"]
                       if c in _df_r.columns]
            st.dataframe(_df_r[_cols_r], use_container_width=True, hide_index=True)
        else:
            st.info("Sin CFDIs recibidos para este periodo.")
    else:
        st.caption("sat_cfdi_list no disponible — " + _rr.get("error", ""))
