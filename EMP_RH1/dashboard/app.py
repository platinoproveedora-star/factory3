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
h1,h2,h3 { color:#e0e0ff; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

_EMPRESA_ID = os.getenv("RH_EMPRESA_ID", "rh_empresa_1")


def _run_skill(nombre: str, context: dict) -> dict:
    import sys
    _root = str(Path(__file__).parent.parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from factory.engine import SkillLoader, SkillRunner
    _base = Path(__file__).parent.parent.parent / "factory"
    ext = _base / "skills" / "externos"
    ext.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(internal_root=_base / "skills" / "internos", external_root=ext)
    return SkillRunner(loader).run(nombre, context, source="internos")


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
        ["Overview", "Vacantes", "Candidatos", "Pipeline", "Entrevistas", "Reclutadores", "Seeds", "Ultima Vacante", "Análisis IA", "Offer Builder", "FB Groups"],
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

    if "fb_grupos_visibles" not in st.session_state:
        st.session_state.fb_grupos_visibles = None

    tab_buscar, tab_historial = st.tabs(["Nueva búsqueda", "Historial"])

    # ── Nueva búsqueda ────────────────────────────────────────────────────────
    with tab_buscar:
        tema = st.text_input(
            "Tema de búsqueda",
            placeholder="operadores de tráiler Mérida · cemento México · maquinaria pesada Chiapas",
        )
        if st.button("Buscar grupos", type="primary", disabled=not tema.strip()):
            with st.spinner("Buscando grupos..."):
                engine_r = _run_skill("fb_groupsearch_engine", {"tema_busqueda": tema.strip(), "dry_run": False})
            if not engine_r.get("ok"):
                st.error(engine_r.get("error", "Error en búsqueda"))
            else:
                ed = engine_r.get("data") or {}
                grupos = ed.get("grupos", [])
                fuente = ed.get("fuente", "ia_sugerido")
                with st.spinner("Guardando resultados..."):
                    saver_r = _run_skill("fb_groupsearch_saver", {
                        "grupos":        grupos,
                        "fuente":        fuente,
                        "tema_busqueda": tema.strip(),
                        "empresa_id":    _EMPRESA_ID,
                        "dry_run":       False,
                    })
                if saver_r.get("ok"):
                    sd = saver_r.get("data") or {}
                    fuente_lbl = "Meta API" if fuente == "meta_api" else "IA sugerido ⚠️"
                    st.success(f"{sd.get('total_grupos', 0)} grupos guardados — {sd.get('search_id')} — Fuente: {fuente_lbl}")
                    st.session_state.fb_grupos_visibles = sd.get("search_id")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(saver_r.get("error", "Error al guardar"))

    # ── Historial ─────────────────────────────────────────────────────────────
    with tab_historial:
        searches = select("fb_gs_searches", f"select=*&order=created_at.desc&limit=200")

        if not searches:
            st.info("Sin búsquedas guardadas. Usa la pestaña Nueva búsqueda.")
        else:
            df_s = pd.DataFrame([{
                "Search ID":  s.get("search_id", ""),
                "Tema":       s.get("tema_busqueda", ""),
                "Grupos":     s.get("total_grupos", 0),
                "Fuente":     s.get("fuente", ""),
                "Estado":     s.get("estado", ""),
                "Fecha":      (s.get("created_at") or "")[:10],
            } for s in searches])
            st.dataframe(df_s, use_container_width=True, hide_index=True)

            selected_id = st.selectbox(
                "Ver grupos de búsqueda",
                options=[s.get("search_id") for s in searches],
                index=0,
            )
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("Ver grupos"):
                    st.session_state.fb_grupos_visibles = selected_id
            with col2:
                if st.button("Borrar búsqueda", type="secondary"):
                    del_r = _run_skill("fb_groupsearch_delete", {"search_id": selected_id, "dry_run": False})
                    if del_r.get("ok"):
                        st.success(f"{selected_id} eliminada.")
                        st.session_state.fb_grupos_visibles = None
                        st.rerun()
                    else:
                        st.error(del_r.get("error", "Error al borrar"))

    # ── Tabla de grupos ───────────────────────────────────────────────────────
    sid_ver = st.session_state.fb_grupos_visibles
    if sid_ver:
        st.divider()
        st.subheader(f"Grupos — {sid_ver}")
        grupos = select("fb_gs_groups", f"select=*&search_id=eq.{sid_ver}&order=created_at.desc&limit=500")

        if not grupos:
            st.info("Sin grupos para esta búsqueda.")
        else:
            df_g = pd.DataFrame([{
                "Nombre":    g.get("grupo_nombre", ""),
                "URL":       g.get("grupo_url", ""),
                "Miembros":  g.get("miembros_estimados", ""),
                "Ubicación": g.get("ubicacion_detectada", ""),
                "Fuente":    g.get("fuente", ""),
                "Descripción": (g.get("descripcion") or "")[:80],
            } for g in grupos])
            st.dataframe(df_g, use_container_width=True, hide_index=True)
