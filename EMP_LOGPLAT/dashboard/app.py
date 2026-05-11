"""LOGPLAT Dashboard — Logística Platino."""
from __future__ import annotations

import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

from db import select, update, insert, delete

st.set_page_config(page_title="LOGPLAT Dashboard", page_icon="🚛", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stSidebar"] { background: #0a0f1a; }
[data-testid="metric-container"] {
    background: #161b2e;
    border-left: 3px solid #4a9eff;
    border-radius: 8px;
    padding: 12px;
}
h1, h2, h3, h4 { color: #f0f4ff !important; }
p, span, div, li { color: #d0d8e8 !important; }
[data-testid="stMarkdownContainer"] p { color: #d0d8e8 !important; }
[data-testid="stMarkdownContainer"] li { color: #d0d8e8 !important; }
label, .stSelectbox label, .stTextInput label, .stDateInput label { color: #c9d1d9 !important; }
.stDataFrame { border: 1px solid #30363d; border-radius: 6px; }
[data-testid="stMetricValue"] { color: #f0b429 !important; font-size: 1.4rem; }
[data-testid="stMetricLabel"] { color: #aab8cc !important; }
[data-testid="stCaptionContainer"] { color: #8b98a8 !important; }
.stRadio label { color: #d0d8e8 !important; }
[data-baseweb="select"] { color: #d0d8e8 !important; }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🚛 LOGPLAT")
    seccion = st.radio("Sección", ["Overview", "Viajes", "Gastos", "Pagos", "CXC", "Análisis"])
    st.divider()
    if st.button("↺ Actualizar"):
        st.cache_data.clear()
        st.rerun()

st.title("🚛 LOGPLAT — Logística Platino")

# ─── DATA LOADERS ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def get_viajes() -> pd.DataFrame:
    rows = select("viajes", "select=*&order=created_at.desc&limit=1000")
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30)
def get_gastos() -> pd.DataFrame:
    rows = select("gastos", "select=*&order=created_at.desc&limit=1000")
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30)
def get_pagos() -> pd.DataFrame:
    rows = select("pagos", "select=*&order=created_at.desc&limit=1000")
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30)
def get_cxc() -> pd.DataFrame:
    rows = select("cuentas_por_cobrar", "select=*&order=created_at.desc&limit=1000")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _badge(val: str) -> str:
    m = {
        "por_cobrar": "🔴 por cobrar", "parcial": "🟡 parcial", "pagado": "🟢 pagado",
        "pendiente":  "🔴 pendiente",  "activo":  "🟢 activo",  "terminado": "⚪ terminado",
    }
    return m.get(str(val).lower(), val or "—")

def _fmt(v) -> str:
    try: return f"${float(v):,.0f}"
    except: return "—"

def _num(v) -> float:
    try: return float(v)
    except: return 0.0

def _date_filter(df: pd.DataFrame, col: str, desde, hasta) -> pd.DataFrame:
    if col not in df.columns: return df
    try:
        s = pd.to_datetime(df[col], errors="coerce")
        if desde: df = df[s >= pd.Timestamp(desde)]
        if hasta: df = df[s <= pd.Timestamp(hasta)]
    except Exception: pass
    return df

def _guardar(tabla: str, df_orig: pd.DataFrame, df_edit: pd.DataFrame):
    if df_orig.empty or "folio" not in df_orig.columns: return
    guardados, errores = 0, 0
    for i in range(min(len(df_orig), len(df_edit))):
        orig = df_orig.iloc[i]
        edit = df_edit.iloc[i]
        cambios = {k: edit[k] for k in df_orig.columns if str(orig.get(k)) != str(edit.get(k)) and k not in ("id","created_at","folio")}
        if cambios:
            ok = update(tabla, str(orig["folio"]), cambios)
            if ok: guardados += 1
            else:  errores += 1
    if guardados: st.success(f"✅ {guardados} fila(s) guardada(s).")
    if errores:   st.error(f"❌ {errores} fila(s) con error.")
    if guardados or errores: st.cache_data.clear()

def _csv_btn(df: pd.DataFrame, nombre: str, key: str):
    st.download_button("📥 Exportar CSV", df.to_csv(index=False).encode("utf-8"),
                       f"{nombre}.csv", "text/csv", key=key)

def _totales(*pairs):
    cols = st.columns(len(pairs))
    for col, (label, val) in zip(cols, pairs):
        col.metric(label, _fmt(val))


# ─── OVERVIEW ─────────────────────────────────────────────────────────────────

if seccion == "Overview":
    st.header("📊 Overview")
    dv = get_viajes()
    dg = get_gastos()
    dp = get_pagos()
    dc = get_cxc()

    r1 = st.columns(4)
    r1[0].metric("Total Viajes",    len(dv))
    r1[1].metric("Viajes Activos",  int((dv["estatus_viaje"] == "activo").sum()) if not dv.empty and "estatus_viaje" in dv.columns else 0)
    r1[2].metric("Total Gastos",    _fmt(dg["monto_gasto"].apply(_num).sum()) if not dg.empty and "monto_gasto" in dg.columns else "$0")
    r1[3].metric("Utilidad Total",  _fmt(dv["utilidad_viaje"].apply(_num).sum()) if not dv.empty and "utilidad_viaje" in dv.columns else "$0")

    st.divider()
    r2 = st.columns(4)
    saldo_pend = dc[dc["estatus_cobro"] != "pagado"]["saldo_pendiente"].apply(_num).sum() if not dc.empty and "saldo_pendiente" in dc.columns else 0
    r2[0].metric("Saldo CXC Pendiente", _fmt(saldo_pend))
    r2[1].metric("Total Cobrado",       _fmt(dc["monto_pagado"].apply(_num).sum()) if not dc.empty and "monto_pagado" in dc.columns else "$0")
    r2[2].metric("Pagos Recibidos",     _fmt(dp["monto_pago"].apply(_num).sum()) if not dp.empty and "monto_pago" in dp.columns else "$0")
    vxc = int((dv["estatus_pago"] == "por_cobrar").sum()) if not dv.empty and "estatus_pago" in dv.columns else 0
    r2[3].metric("Viajes por Cobrar", vxc)

    # ── Último Viaje ───────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📦 Último Viaje")
    if not dv.empty and "fecha_salida" in dv.columns:
        _dv_s = dv.copy()
        _dv_s["_f"] = pd.to_datetime(_dv_s["fecha_salida"], errors="coerce")
        _ult  = _dv_s.sort_values("_f", ascending=False).iloc[0]
        _fu   = _ult["folio"]
        _costo_u = dg[dg["numero_viaje"] == _fu]["monto_gasto"].apply(_num).sum() if not dg.empty and "numero_viaje" in dg.columns else 0
        _util_u  = _num(_ult.get("precio_venta_viaje", 0)) - _costo_u
        _u1, _u2, _u3, _u4 = st.columns(4)
        _u1.metric("Folio",        _fu)
        _u2.metric("Destino",      str(_ult.get("destino","—") or "—")[:30])
        _u3.metric("Precio Venta", _fmt(_ult.get("precio_venta_viaje", 0)))
        _u4.metric("Utilidad",     _fmt(_util_u))
        _gv_det = dg[dg["numero_viaje"] == _fu] if not dg.empty and "numero_viaje" in dg.columns else pd.DataFrame()
        if not _gv_det.empty:
            st.caption("Gastos:")
            _gc = [c for c in ["folio","fecha_gasto","concepto","monto_gasto","tipo_gasto","chofer"] if c in _gv_det.columns]
            st.dataframe(_gv_det[_gc].reset_index(drop=True), use_container_width=True, hide_index=True)
        else:
            st.caption("Sin gastos registrados para este viaje.")
        _pv = dp[dp["numero_viaje"] == _fu] if not dp.empty and "numero_viaje" in dp.columns else pd.DataFrame()
        if not _pv.empty:
            st.caption("Pagos:")
            _pc = [c for c in ["folio","fecha_pago","monto_pago","metodo_pago"] if c in _pv.columns]
            st.dataframe(_pv[_pc].reset_index(drop=True), use_container_width=True, hide_index=True)
        else:
            st.caption("Sin pagos registrados para este viaje.")
    else:
        st.info("Sin viajes registrados.")

    # ── Viajes del mes en curso ────────────────────────────────────────────────
    st.divider()
    _hoy_ov = date.today()
    st.subheader(f"📅 Viajes {_hoy_ov.strftime('%B %Y').title()}")
    if not dv.empty and "fecha_salida" in dv.columns:
        _dv_m = dv.copy()
        _dv_m["_f"] = pd.to_datetime(_dv_m["fecha_salida"], errors="coerce")
        _dv_m = _dv_m[(_dv_m["_f"].dt.month == _hoy_ov.month) & (_dv_m["_f"].dt.year == _hoy_ov.year)]
        if _dv_m.empty:
            st.info(f"Sin viajes en {_hoy_ov.strftime('%B %Y')}.")
        else:
            if not dg.empty and "numero_viaje" in dg.columns:
                _cm = (dg.assign(_mg=dg["monto_gasto"].apply(_num))
                          .groupby("numero_viaje")["_mg"].sum().reset_index()
                          .rename(columns={"numero_viaje": "folio", "_mg": "costo_viaje"}))
                _dv_m = _dv_m.drop(columns=["costo_viaje"], errors="ignore").merge(_cm, on="folio", how="left")
                _dv_m["costo_viaje"] = _dv_m["costo_viaje"].fillna(0)
            _dv_m["utilidad_viaje"] = _dv_m["precio_venta_viaje"].apply(_num) - _dv_m["costo_viaje"].apply(_num)
            _mc = [c for c in ["folio","destino","chofer","fecha_salida","precio_venta_viaje","costo_viaje","utilidad_viaje","estatus_pago"] if c in _dv_m.columns]
            st.dataframe(_dv_m[_mc].reset_index(drop=True), use_container_width=True, hide_index=True)
            _mm1, _mm2, _mm3 = st.columns(3)
            _mm1.metric("Venta Mes",    _fmt(_dv_m["precio_venta_viaje"].apply(_num).sum()))
            _mm2.metric("Costo Mes",    _fmt(_dv_m["costo_viaje"].apply(_num).sum()))
            _mm3.metric("Utilidad Mes", _fmt(_dv_m["utilidad_viaje"].apply(_num).sum()))
    else:
        st.info("Sin viajes registrados.")


# ─── VIAJES ───────────────────────────────────────────────────────────────────

elif seccion == "Viajes":
    st.header("🚚 Viajes")
    df  = get_viajes()
    dg_ = get_gastos()
    if df.empty:
        st.info("Sin viajes registrados.")
        st.stop()

    # Costo = suma de gastos por viaje (calculado, no editable)
    if not dg_.empty and "numero_viaje" in dg_.columns and "monto_gasto" in dg_.columns:
        _costos = (dg_.copy()
                     .assign(monto_gasto=dg_["monto_gasto"].apply(_num))
                     .groupby("numero_viaje")["monto_gasto"].sum()
                     .reset_index()
                     .rename(columns={"numero_viaje": "folio", "monto_gasto": "costo_viaje"}))
        df = df.drop(columns=["costo_viaje"], errors="ignore").merge(_costos, on="folio", how="left")
        df["costo_viaje"] = df["costo_viaje"].fillna(0)
    df["utilidad_viaje"] = df["precio_venta_viaje"].apply(_num) - df["costo_viaje"].apply(_num)

    c1, c2, c3, c4, c5 = st.columns(5)
    buscar   = c1.text_input("Cliente", key="v_cli")
    ep_fil   = c2.selectbox("Estatus Pago",  ["Todos","por_cobrar","parcial","pagado"], key="v_ep")
    ev_fil   = c3.selectbox("Estatus Viaje", ["Todos","activo","terminado"], key="v_ev")
    f_desde  = c4.date_input("Desde", value=None, key="v_d")
    f_hasta  = c5.date_input("Hasta", value=None, key="v_h")

    dff = df.copy()
    if buscar and "cliente" in dff.columns: dff = dff[dff["cliente"].str.contains(buscar, case=False, na=False)]
    if ep_fil != "Todos" and "estatus_pago"  in dff.columns: dff = dff[dff["estatus_pago"]  == ep_fil]
    if ev_fil != "Todos" and "estatus_viaje" in dff.columns: dff = dff[dff["estatus_viaje"] == ev_fil]
    dff = _date_filter(dff, "fecha_salida", f_desde, f_hasta)

    st.caption(f"{len(dff)} viaje(s)")
    cols_show = [c for c in ["folio","cliente","origen","destino","fecha_salida","fecha_llegada",
                              "chofer","costo_viaje","precio_venta_viaje","utilidad_viaje",
                              "estatus_pago","estatus_viaje","id_doc"] if c in dff.columns]
    orig = dff[cols_show].copy()
    edit = st.data_editor(orig, use_container_width=True, key="edit_viajes", num_rows="fixed",
                          disabled=["folio","costo_viaje","utilidad_viaje"])

    bc, ac, ec = st.columns(3)
    if bc.button("💾 Guardar cambios", key="save_v"): _guardar("viajes", orig, edit)
    if ac.button("➕ Agregar Viaje", key="add_v"):
        _folios = df["folio"].dropna().str.extract(r"(\d+)")[0].apply(_num)
        _next   = int(_folios.max()) + 1 if not _folios.empty else 1
        _nuevo  = f"VIA-{str(_next).zfill(3)}"
        if insert("viajes", {"folio": _nuevo, "estatus_pago": "por_cobrar", "estatus_viaje": "activo"}):
            insert("cuentas_por_cobrar", {
                "folio": f"CXC-{str(_next).zfill(3)}",
                "numero_viaje": _nuevo,
                "monto_total": 0, "monto_pagado": 0,
                "saldo_pendiente": 0, "estatus_cobro": "pendiente",
            })
            st.success(f"✅ Viaje {_nuevo} creado.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Error al crear el viaje.")
    _csv_btn(dff, "viajes", "csv_v")

    with st.expander("🗑️ Borrar viaje"):
        _del_v = st.selectbox("Folio", ["—"] + sorted(df["folio"].dropna().tolist()), key="del_v_sel")
        if st.button("⚠️ Confirmar borrar", key="del_v_btn") and _del_v != "—":
            delete("cuentas_por_cobrar", f"CXC-{_del_v.split('-',1)[1]}")
            if delete("viajes", _del_v):
                st.success(f"Borrado {_del_v}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Error al borrar.")

    st.divider()
    nums = ["costo_viaje","precio_venta_viaje","utilidad_viaje"]
    _totales(*[(c.replace("_"," ").title(), dff[c].apply(_num).sum()) for c in nums if c in dff.columns])


# ─── GASTOS ───────────────────────────────────────────────────────────────────

elif seccion == "Gastos":
    st.header("💸 Gastos")
    df = get_gastos()
    if df.empty:
        st.info("Sin gastos registrados.")
        st.stop()

    c1, c2, c3, c4, c5 = st.columns(5)
    buscar  = c1.text_input("Concepto", key="g_conc")
    tg_fil  = c2.selectbox("Tipo Gasto", ["Todos","diesel","casetas","comida","reparacion","maniobra","otro"], key="g_tipo")
    nv_fil  = c3.text_input("Núm. Viaje", key="g_nv")
    f_desde = c4.date_input("Desde", value=None, key="g_d")
    f_hasta = c5.date_input("Hasta", value=None, key="g_h")

    dff = df.copy()
    if buscar and "concepto" in dff.columns:    dff = dff[dff["concepto"].str.contains(buscar, case=False, na=False)]
    if tg_fil != "Todos" and "tipo_gasto" in dff.columns: dff = dff[dff["tipo_gasto"] == tg_fil]
    if nv_fil and "numero_viaje" in dff.columns: dff = dff[dff["numero_viaje"].str.contains(nv_fil, case=False, na=False)]
    dff = _date_filter(dff, "fecha_gasto", f_desde, f_hasta)

    st.caption(f"{len(dff)} gasto(s)")
    cols_show = [c for c in ["folio","numero_viaje","fecha_gasto","concepto","monto_gasto",
                              "tipo_gasto","chofer","id_doc"] if c in dff.columns]
    orig = dff[cols_show].copy()
    edit = st.data_editor(orig, use_container_width=True, key="edit_gastos", num_rows="fixed",
                          disabled=["folio"])

    bc, ac, _ = st.columns(3)
    if bc.button("💾 Guardar cambios", key="save_g"): _guardar("gastos", orig, edit)
    if ac.button("➕ Agregar Gasto", key="add_g"):
        _folios = df["folio"].dropna().str.extract(r"(\d+)")[0].apply(_num)
        _next   = int(_folios.max()) + 1 if not _folios.empty else 1
        _nuevo  = f"GAS-{str(_next).zfill(3)}"
        if insert("gastos", {"folio": _nuevo}):
            st.success(f"✅ Gasto {_nuevo} creado. Edítalo en la tabla.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Error al crear el gasto.")
    _csv_btn(dff, "gastos", "csv_g")

    with st.expander("🗑️ Borrar gasto"):
        _del_g = st.selectbox("Folio", ["—"] + sorted(df["folio"].dropna().tolist()), key="del_g_sel")
        if st.button("⚠️ Confirmar borrar", key="del_g_btn") and _del_g != "—":
            if delete("gastos", _del_g):
                st.success(f"Borrado {_del_g}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Error al borrar.")

    st.divider()
    total_g = dff["monto_gasto"].apply(_num).sum() if "monto_gasto" in dff.columns else 0
    st.metric("Total Gastos Filtrados", _fmt(total_g))

    st.subheader("📋 Gastos por Tipo")
    if "tipo_gasto" in dff.columns and "monto_gasto" in dff.columns:
        _gt = dff.copy()
        _gt["tipo_gasto"]  = _gt["tipo_gasto"].str.strip().str.lower().fillna("sin tipo")
        _gt["monto_gasto"] = _gt["monto_gasto"].apply(_num)
        grp = (_gt.groupby("tipo_gasto")["monto_gasto"]
                  .agg(Cantidad="count", Monto="sum").reset_index()
                  .rename(columns={"tipo_gasto": "Tipo"}))
        grp["% del Total"] = grp["Monto"].apply(lambda x: f"{x/total_g*100:.1f}%" if total_g else "0%")
        grp["Monto"]       = grp["Monto"].apply(_fmt)
        st.dataframe(grp, use_container_width=True, hide_index=True)

    st.divider()

    # ── Gastos del mes actual ─────────────────────────────────────────────────
    hoy = date.today()
    st.subheader(f"🗓️ Gastos — {hoy.strftime('%B %Y').title()}")
    if "fecha_gasto" in df.columns and "monto_gasto" in df.columns:
        _df_mes = df.copy()
        _df_mes["_f"] = pd.to_datetime(_df_mes["fecha_gasto"], errors="coerce")
        _df_mes = _df_mes[(_df_mes["_f"].dt.month == hoy.month) & (_df_mes["_f"].dt.year == hoy.year)]
        if _df_mes.empty:
            st.info("Sin gastos en el mes actual.")
        else:
            _cols_m = [c for c in ["folio","fecha_gasto","concepto","monto_gasto","tipo_gasto","chofer","numero_viaje"] if c in _df_mes.columns]
            st.dataframe(
                _df_mes[_cols_m].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "folio":         st.column_config.TextColumn("Folio",    width="small"),
                    "fecha_gasto":   st.column_config.DateColumn("Fecha",    format="DD/MM/YYYY"),
                    "concepto":      st.column_config.TextColumn("Concepto"),
                    "monto_gasto":   st.column_config.NumberColumn("Monto",  format="$%,.0f"),
                    "tipo_gasto":    st.column_config.TextColumn("Tipo",     width="small"),
                    "chofer":        st.column_config.TextColumn("Chofer",   width="medium"),
                    "numero_viaje":  st.column_config.TextColumn("Viaje",    width="small"),
                },
            )
            st.metric(f"Total {hoy.strftime('%B').title()}", _fmt(_df_mes["monto_gasto"].apply(_num).sum()))

    st.divider()

    # ── Filtro por mes ────────────────────────────────────────────────────────
    st.subheader("📆 Ver Gastos por Mes")
    if "fecha_gasto" in df.columns:
        _tmp = df.copy()
        _tmp["_f"] = pd.to_datetime(_tmp["fecha_gasto"], errors="coerce")
        _tmp["_mes"] = _tmp["_f"].dt.to_period("M")
        _meses = sorted(_tmp["_mes"].dropna().unique().astype(str), reverse=True)
    else:
        _meses = []

    if _meses:
        mes_sel = st.selectbox("Mes", _meses, key="g_mes_sel")
        _df_filtrado = df.copy()
        _df_filtrado["_f"]   = pd.to_datetime(_df_filtrado["fecha_gasto"], errors="coerce")
        _df_filtrado["_mes"] = _df_filtrado["_f"].dt.to_period("M").astype(str)
        _df_filtrado = _df_filtrado[_df_filtrado["_mes"] == mes_sel]
        _cols_m2 = [c for c in ["folio","fecha_gasto","concepto","monto_gasto","tipo_gasto","chofer","numero_viaje"] if c in _df_filtrado.columns]
        if _df_filtrado.empty:
            st.info(f"Sin gastos en {mes_sel}.")
        else:
            st.dataframe(
                _df_filtrado[_cols_m2].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "folio":         st.column_config.TextColumn("Folio",    width="small"),
                    "fecha_gasto":   st.column_config.DateColumn("Fecha",    format="DD/MM/YYYY"),
                    "concepto":      st.column_config.TextColumn("Concepto"),
                    "monto_gasto":   st.column_config.NumberColumn("Monto",  format="$%,.0f"),
                    "tipo_gasto":    st.column_config.TextColumn("Tipo",     width="small"),
                    "chofer":        st.column_config.TextColumn("Chofer"),
                    "numero_viaje":  st.column_config.TextColumn("Viaje",    width="small"),
                },
            )
            st.metric(f"Total {mes_sel}", _fmt(_df_filtrado["monto_gasto"].apply(_num).sum()))
    else:
        st.info("Sin gastos con fecha registrada.")


# ─── PAGOS ────────────────────────────────────────────────────────────────────

elif seccion == "Pagos":
    st.header("💰 Pagos")
    df = get_pagos()
    if df.empty:
        st.info("Sin pagos registrados.")
        st.stop()

    c1, c2, c3, c4, c5 = st.columns(5)
    buscar  = c1.text_input("Cliente", key="p_cli")
    mp_fil  = c2.selectbox("Método Pago", ["Todos","transferencia","efectivo","cheque"], key="p_mp")
    nv_fil  = c3.text_input("Núm. Viaje", key="p_nv")
    f_desde = c4.date_input("Desde", value=None, key="p_d")
    f_hasta = c5.date_input("Hasta", value=None, key="p_h")

    dff = df.copy()
    if buscar and "cliente" in dff.columns: dff = dff[dff["cliente"].str.contains(buscar, case=False, na=False)]
    if mp_fil != "Todos" and "metodo_pago" in dff.columns: dff = dff[dff["metodo_pago"] == mp_fil]
    if nv_fil and "numero_viaje" in dff.columns: dff = dff[dff["numero_viaje"].fillna("").str.contains(nv_fil, case=False, na=False)]
    dff = _date_filter(dff, "fecha_pago", f_desde, f_hasta)

    st.caption(f"{len(dff)} pago(s)")
    cols_show = [c for c in ["folio","numero_viaje","fecha_pago","cliente","monto_pago",
                              "metodo_pago","observaciones","id_doc"] if c in dff.columns]
    orig = dff[cols_show].copy()
    edit = st.data_editor(orig, use_container_width=True, key="edit_pagos", num_rows="fixed",
                          disabled=["folio"])

    bc, ac, _ = st.columns(3)
    if bc.button("💾 Guardar cambios", key="save_p"): _guardar("pagos", orig, edit)
    if ac.button("➕ Agregar Pago", key="add_p"):
        _folios = df["folio"].dropna().str.extract(r"(\d+)")[0].apply(_num)
        _next   = int(_folios.max()) + 1 if not _folios.empty else 1
        _nuevo  = f"PAG-{str(_next).zfill(3)}"
        if insert("pagos", {"folio": _nuevo}):
            st.success(f"✅ Pago {_nuevo} creado. Edítalo en la tabla.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Error al crear el pago.")
    _csv_btn(dff, "pagos", "csv_p")

    with st.expander("🗑️ Borrar pago"):
        _del_p = st.selectbox("Folio", ["—"] + sorted(df["folio"].dropna().tolist()), key="del_p_sel")
        if st.button("⚠️ Confirmar borrar", key="del_p_btn") and _del_p != "—":
            if delete("pagos", _del_p):
                st.success(f"Borrado {_del_p}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Error al borrar.")

    st.divider()
    st.metric("Total Pagos Filtrados", _fmt(dff["monto_pago"].apply(_num).sum()) if "monto_pago" in dff.columns else "$0")


# ─── CXC ──────────────────────────────────────────────────────────────────────

elif seccion == "CXC":
    st.header("📋 Cuentas por Cobrar")
    df  = get_cxc()
    dp  = get_pagos()

    # Solo filtros — CXC es resultado de viajes vs pagos, no se edita directamente
    c1, c2, c3, c4 = st.columns(4)
    buscar  = c1.text_input("Cliente", key="c_cli")
    ec_fil  = c2.selectbox("Estatus", ["Todos","pendiente","parcial","pagado"], key="c_ec")
    f_desde = c3.date_input("Desde", value=None, key="c_d")
    f_hasta = c4.date_input("Hasta", value=None, key="c_h")

    dff = df.copy() if not df.empty else pd.DataFrame()
    if not dff.empty:
        if buscar and "cliente" in dff.columns:
            dff = dff[dff["cliente"].str.contains(buscar, case=False, na=False)]
        if ec_fil != "Todos" and "estatus_cobro" in dff.columns:
            dff = dff[dff["estatus_cobro"] == ec_fil]
        dff = _date_filter(dff, "fecha_viaje", f_desde, f_hasta)
        if "fecha_viaje" in dff.columns and "estatus_cobro" in dff.columns:
            hoy = pd.Timestamp(date.today())
            fv  = pd.to_datetime(dff["fecha_viaje"], errors="coerce")
            dff["dias_pendiente"] = (hoy - fv).dt.days.where(
                dff["estatus_cobro"] != "pagado", 0).fillna(0).astype(int)

    _cxc_cols = [c for c in ["folio","cliente","numero_viaje","monto_total","monto_pagado",
                               "saldo_pendiente","estatus_cobro","dias_pendiente",
                               "fecha_viaje","fecha_vencimiento"] if not dff.empty and c in dff.columns]

    # ── Arriba: Por Cobrar / Parciales ────────────────────────────────────────
    st.subheader("🔴 Por Cobrar")
    if not dff.empty and "estatus_cobro" in dff.columns:
        _pend = dff[~dff["estatus_cobro"].isin(["pagado"])]
        if _pend.empty:
            st.success("✅ Todas las cuentas están liquidadas.")
        else:
            st.caption(f"{len(_pend)} cuenta(s) pendiente(s)")
            st.dataframe(_pend[[c for c in _cxc_cols if c in _pend.columns]],
                         use_container_width=True, hide_index=True)
            _cm1, _cm2, _cm3 = st.columns(3)
            _cm1.metric("Saldo Pendiente", _fmt(_pend["saldo_pendiente"].apply(_num).sum()) if "saldo_pendiente" in _pend.columns else "$0")
            _cm2.metric("Total Facturado", _fmt(_pend["monto_total"].apply(_num).sum()) if "monto_total" in _pend.columns else "$0")
            _cm3.metric("Días Promedio",   f"{_pend['dias_pendiente'].mean():.0f}" if "dias_pendiente" in _pend.columns and len(_pend) > 0 else "—")
    else:
        st.info("Sin cuentas por cobrar." if dff.empty else "✅ Todas liquidadas.")

    if not dff.empty:
        _csv_btn(dff, "cxc", "csv_c")

    st.divider()

    # ── Abajo: Viajes pagados + detalle de pago ───────────────────────────────
    st.subheader("🟢 Viajes Pagados")
    if not dff.empty and "estatus_cobro" in dff.columns:
        _pag = dff[dff["estatus_cobro"] == "pagado"]
        if _pag.empty:
            st.info("Sin viajes pagados aún.")
        else:
            if not dp.empty and "numero_viaje" in dp.columns and "numero_viaje" in _pag.columns:
                _p_cols = [c for c in ["folio","numero_viaje","fecha_pago","monto_pago","metodo_pago"] if c in dp.columns]
                _joined = _pag.merge(
                    dp[_p_cols].rename(columns={"folio": "folio_pago"}),
                    on="numero_viaje", how="left"
                )
                _show = [c for c in ["folio","cliente","numero_viaje","monto_total",
                                      "folio_pago","fecha_pago","monto_pago","metodo_pago"] if c in _joined.columns]
                st.caption(f"{len(_pag)} viaje(s) pagado(s)")
                st.dataframe(_joined[_show], use_container_width=True, hide_index=True)
            else:
                st.dataframe(_pag[[c for c in _cxc_cols if c in _pag.columns]],
                             use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de cuentas.")

    if not dff.empty:
        st.divider()
        _rc1, _rc2 = st.columns(2)
        _rc1.metric("Total CXC",     _fmt(dff["monto_total"].apply(_num).sum()) if "monto_total" in dff.columns else "$0")
        _rc2.metric("Total Cobrado", _fmt(dff["monto_pagado"].apply(_num).sum()) if "monto_pagado" in dff.columns else "$0")


# ─── ANÁLISIS ─────────────────────────────────────────────────────────────────

elif seccion == "Análisis":
    st.header("📈 Análisis")
    dv = get_viajes()
    dg = get_gastos()
    dc = get_cxc()

    # 1. Gastos sin viaje (arriba — pendiente de asignar)
    st.subheader("⚠️ Gastos sin Viaje Asociado")
    if not dg.empty and "numero_viaje" in dg.columns:
        sin_viaje = dg[dg["numero_viaje"].isna() | (dg["numero_viaje"] == "")]
        if sin_viaje.empty:
            st.success("✅ Todos los gastos tienen viaje asociado.")
        else:
            _sv_cols = [c for c in ["folio","fecha_gasto","concepto","monto_gasto","tipo_gasto","chofer","numero_viaje"] if c in sin_viaje.columns]
            sv_orig = sin_viaje[_sv_cols].copy()
            sv_edit = st.data_editor(
                sv_orig, use_container_width=True, hide_index=True, key="edit_sv", num_rows="fixed",
                disabled=[c for c in _sv_cols if c != "numero_viaje"],
                column_config={"numero_viaje": st.column_config.TextColumn("Viaje (editar)", help="Ej: VIA-001")},
            )
            if st.button("💾 Actualizar Viaje", key="save_sv"):
                _guardar("gastos", sv_orig, sv_edit)
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("Sin datos de gastos.")

    st.divider()

    # 2. Viajes sin gastos
    st.subheader("⚠️ Viajes sin Gastos Registrados")
    if not dv.empty and not dg.empty and "folio" in dv.columns and "numero_viaje" in dg.columns:
        folios_con_gasto = set(dg["numero_viaje"].dropna().unique())
        sin_gastos = dv[~dv["folio"].isin(folios_con_gasto)]
        if sin_gastos.empty:
            st.success("✅ Todos los viajes tienen gastos registrados.")
        else:
            _sg_cols = [c for c in ["folio","cliente","origen","destino","fecha_salida","estatus_viaje"] if c in sin_gastos.columns]
            st.dataframe(sin_gastos[_sg_cols], use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos suficientes.")

    st.divider()

    # 3. Gastos por camión/chofer × mes
    st.subheader("🚛 Gastos por Camión × Mes")
    if not dg.empty and "monto_gasto" in dg.columns and "fecha_gasto" in dg.columns:
        _gcm = dg.copy()
        _gcm["monto_gasto"] = _gcm["monto_gasto"].apply(_num)
        _gcm["_f"]  = pd.to_datetime(_gcm["fecha_gasto"], errors="coerce")
        _gcm["mes"] = _gcm["_f"].dt.to_period("M").astype(str)
        _ucol = next((c for c in ["camion","unidad","chofer"] if c in _gcm.columns), None)
        if _ucol:
            _pivot = (_gcm.groupby([_ucol, "mes"])["monto_gasto"]
                         .sum().unstack("mes").fillna(0).reset_index())
            _pivot.columns.name = None
            _pivot = _pivot.rename(columns={_ucol: "Chofer/Camión"})
            for _c in _pivot.columns[1:]:
                _pivot[_c] = _pivot[_c].apply(lambda x: _fmt(x) if _num(x) > 0 else "—")
            st.dataframe(_pivot, use_container_width=True, hide_index=True)
        else:
            st.info("Sin columna de camión o chofer en gastos.")
    else:
        st.info("Sin datos suficientes.")

    st.divider()

    # 4. Utilidad por semana
    st.subheader("📅 Utilidad por Semana")
    if not dv.empty and "fecha_salida" in dv.columns and "utilidad_viaje" in dv.columns:
        dv2 = dv.copy()
        dv2["_util"]        = dv2["utilidad_viaje"].apply(_num)
        dv2["fecha_salida"] = pd.to_datetime(dv2["fecha_salida"], errors="coerce")
        dv2["semana"]       = dv2["fecha_salida"].dt.to_period("W").astype(str)
        semanal = dv2.groupby("semana")["_util"].sum().reset_index()
        semanal.columns = ["Semana","Utilidad"]
        semanal["Utilidad"] = semanal["Utilidad"].apply(_fmt)
        st.dataframe(semanal, use_container_width=True, hide_index=True,
                     column_config={"Semana":   st.column_config.TextColumn("Semana",   width="medium"),
                                    "Utilidad": st.column_config.TextColumn("Utilidad", width="small")})
    else:
        st.info("Sin datos suficientes para utilidad por semana.")

    st.divider()

    # 5. Gastos por tipo
    st.subheader("📋 Gastos por Tipo")
    if not dg.empty and "tipo_gasto" in dg.columns and "monto_gasto" in dg.columns:
        _gt = dg.copy()
        _gt["tipo_gasto"]  = _gt["tipo_gasto"].str.strip().str.lower().fillna("sin tipo")
        _gt["monto_gasto"] = _gt["monto_gasto"].apply(_num)
        _total_g = _gt["monto_gasto"].sum()
        grp = (_gt.groupby("tipo_gasto")["monto_gasto"]
                  .agg(Cantidad="count", Monto="sum").reset_index()
                  .rename(columns={"tipo_gasto": "Tipo"}))
        grp["% del Total"] = grp["Monto"].apply(lambda x: f"{x/_total_g*100:.1f}%" if _total_g else "0%")
        grp["Monto"]       = grp["Monto"].apply(_fmt)
        st.dataframe(grp, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de gastos.")

    st.divider()

    # 6. Top 5 clientes (al final)
    st.subheader("🏆 Top 5 Clientes por Venta")
    if not dv.empty and "cliente" in dv.columns:
        _dv_t = dv.copy()
        _dv_t["_venta"] = _dv_t["precio_venta_viaje"].apply(_num)
        top = _dv_t.groupby("cliente").agg(
            Viajes=("folio","count"), Venta_Total=("_venta","sum"),
        ).reset_index().sort_values("Venta_Total", ascending=False).head(5)
        if not dc.empty and "cliente" in dc.columns:
            _dc_t = dc.copy()
            _dc_t["_cobrado"] = _dc_t["monto_pagado"].apply(_num)
            cobrado = _dc_t.groupby("cliente")["_cobrado"].sum().reset_index()
            cobrado.columns = ["cliente","Cobrado"]
            top = top.merge(cobrado, on="cliente", how="left").fillna(0)
            top["Saldo"]   = (top["Venta_Total"] - top["Cobrado"]).apply(_fmt)
            top["Cobrado"] = top["Cobrado"].apply(_fmt)
        top["Venta_Total"] = top["Venta_Total"].apply(_fmt)
        st.dataframe(top, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de viajes.")

    st.divider()

    # 7. Rentabilidad por chofer (al final)
    st.subheader("👷 Rentabilidad por Chofer")
    if not dv.empty and "chofer" in dv.columns:
        _dv_r = dv.copy()
        _dv_r["_util"] = _dv_r["utilidad_viaje"].apply(_num)
        rv = _dv_r.groupby("chofer").agg(
            Viajes=("folio","count"), Utilidad_Viajes=("_util","sum"),
        ).reset_index()
        if not dg.empty and "chofer" in dg.columns:
            _dg_r = dg.copy()
            _dg_r["_gasto"] = _dg_r["monto_gasto"].apply(_num)
            rg = _dg_r.groupby("chofer")["_gasto"].sum().reset_index()
            rg.columns = ["chofer","Gastos"]
            rv = rv.merge(rg, on="chofer", how="left").fillna(0)
            rv["Utilidad_Neta"] = (rv["Utilidad_Viajes"] - rv["Gastos"]).apply(_fmt)
            rv["Gastos"]        = rv["Gastos"].apply(_fmt)
        rv["Utilidad_Viajes"] = rv["Utilidad_Viajes"].apply(_fmt)
        st.dataframe(rv, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de viajes.")
