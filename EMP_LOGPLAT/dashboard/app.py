"""LOGPLAT Dashboard — Logística Platino."""
from __future__ import annotations

import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

from db import select, update

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
h1, h2, h3 { color: #e0e0ff; }
.stDataFrame { border: 1px solid #30363d; border-radius: 6px; }
label { color: #c9d1d9 !important; }
[data-testid="stMetricValue"] { color: #f0b429; font-size: 1.4rem; }
[data-testid="stMetricLabel"] { color: #c9d1d9; }
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


# ─── VIAJES ───────────────────────────────────────────────────────────────────

elif seccion == "Viajes":
    st.header("🚚 Viajes")
    df = get_viajes()
    if df.empty:
        st.info("Sin viajes registrados.")
        st.stop()

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
    edit = st.data_editor(orig, use_container_width=True, key="edit_viajes", num_rows="fixed")

    bc, ec = st.columns(2)
    if bc.button("💾 Guardar cambios", key="save_v"): _guardar("viajes", orig, edit)
    _csv_btn(dff, "viajes", "csv_v")

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
    cols_show = [c for c in ["folio","fecha_gasto","concepto","monto_gasto","tipo_gasto",
                              "chofer","numero_viaje","id_doc"] if c in dff.columns]
    orig = dff[cols_show].copy()
    edit = st.data_editor(orig, use_container_width=True, key="edit_gastos", num_rows="fixed")

    bc, _ = st.columns(2)
    if bc.button("💾 Guardar cambios", key="save_g"): _guardar("gastos", orig, edit)
    _csv_btn(dff, "gastos", "csv_g")

    st.divider()
    total_g = dff["monto_gasto"].apply(_num).sum() if "monto_gasto" in dff.columns else 0
    st.metric("Total Gastos Filtrados", _fmt(total_g))

    st.subheader("📋 Gastos por Tipo")
    if "tipo_gasto" in dff.columns and "monto_gasto" in dff.columns:
        grp = (dff.groupby("tipo_gasto")["monto_gasto"]
               .agg(["count","sum"]).reset_index()
               .rename(columns={"tipo_gasto":"Tipo","count":"Cantidad","sum":"Monto Total"}))
        grp["Monto Total"] = grp["Monto Total"].apply(lambda x: _fmt(x))
        grp["% del Total"] = dff.groupby("tipo_gasto")["monto_gasto"].sum().apply(
            lambda x: f"{x/total_g*100:.1f}%" if total_g else "0%").values
        st.dataframe(grp, use_container_width=True, hide_index=True)


# ─── PAGOS ────────────────────────────────────────────────────────────────────

elif seccion == "Pagos":
    st.header("💰 Pagos")
    df = get_pagos()
    if df.empty:
        st.info("Sin pagos registrados.")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    buscar  = c1.text_input("Cliente", key="p_cli")
    mp_fil  = c2.selectbox("Método Pago", ["Todos","transferencia","efectivo","cheque"], key="p_mp")
    f_desde = c3.date_input("Desde", value=None, key="p_d")
    f_hasta = c4.date_input("Hasta", value=None, key="p_h")

    dff = df.copy()
    if buscar and "cliente" in dff.columns: dff = dff[dff["cliente"].str.contains(buscar, case=False, na=False)]
    if mp_fil != "Todos" and "metodo_pago" in dff.columns: dff = dff[dff["metodo_pago"] == mp_fil]
    dff = _date_filter(dff, "fecha_pago", f_desde, f_hasta)

    st.caption(f"{len(dff)} pago(s)")
    cols_show = [c for c in ["folio","fecha_pago","cliente","monto_pago","metodo_pago",
                              "numero_viaje","observaciones","id_doc"] if c in dff.columns]
    orig = dff[cols_show].copy()
    edit = st.data_editor(orig, use_container_width=True, key="edit_pagos", num_rows="fixed")

    bc, _ = st.columns(2)
    if bc.button("💾 Guardar cambios", key="save_p"): _guardar("pagos", orig, edit)
    _csv_btn(dff, "pagos", "csv_p")

    st.divider()
    st.metric("Total Pagos Filtrados", _fmt(dff["monto_pago"].apply(_num).sum()) if "monto_pago" in dff.columns else "$0")


# ─── CXC ──────────────────────────────────────────────────────────────────────

elif seccion == "CXC":
    st.header("📋 Cuentas por Cobrar")
    df = get_cxc()
    if df.empty:
        st.info("Sin cuentas por cobrar.")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    buscar  = c1.text_input("Cliente", key="c_cli")
    ec_fil  = c2.selectbox("Estatus", ["Todos","pendiente","parcial","pagado"], key="c_ec")
    f_desde = c3.date_input("Desde", value=None, key="c_d")
    f_hasta = c4.date_input("Hasta", value=None, key="c_h")

    dff = df.copy()
    if buscar and "cliente" in dff.columns: dff = dff[dff["cliente"].str.contains(buscar, case=False, na=False)]
    if ec_fil != "Todos" and "estatus_cobro" in dff.columns: dff = dff[dff["estatus_cobro"] == ec_fil]
    dff = _date_filter(dff, "fecha_viaje", f_desde, f_hasta)

    if "fecha_viaje" in dff.columns and "estatus_cobro" in dff.columns:
        hoy = pd.Timestamp(date.today())
        fv  = pd.to_datetime(dff["fecha_viaje"], errors="coerce")
        dff["dias_pendiente"] = (hoy - fv).dt.days.where(dff["estatus_cobro"] != "pagado", 0).fillna(0).astype(int)

    st.caption(f"{len(dff)} cuenta(s)")
    cols_show = [c for c in ["folio","cliente","numero_viaje","monto_total","monto_pagado",
                              "saldo_pendiente","estatus_cobro","dias_pendiente","fecha_viaje","fecha_vencimiento"] if c in dff.columns]
    orig = dff[cols_show].copy()
    edit = st.data_editor(orig, use_container_width=True, key="edit_cxc", num_rows="fixed")

    bc, _ = st.columns(2)
    if bc.button("💾 Guardar cambios", key="save_c"): _guardar("cuentas_por_cobrar", orig, edit)
    _csv_btn(dff, "cxc", "csv_c")

    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Saldo Pendiente Total", _fmt(dff["saldo_pendiente"].apply(_num).sum()) if "saldo_pendiente" in dff.columns else "$0")
    c2.metric("Total Cobrado",         _fmt(dff["monto_pagado"].apply(_num).sum()) if "monto_pagado" in dff.columns else "$0")

    st.subheader("👥 Resumen por Cliente")
    if "cliente" in dff.columns:
        grp = dff.groupby("cliente").agg(
            Viajes=("numero_viaje","count"),
            Total=("monto_total","sum"),
            Cobrado=("monto_pagado","sum"),
            Saldo=("saldo_pendiente","sum"),
        ).reset_index().sort_values("Saldo", ascending=False)
        for col in ["Total","Cobrado","Saldo"]:
            grp[col] = grp[col].apply(_fmt)
        st.dataframe(grp, use_container_width=True, hide_index=True)


# ─── ANÁLISIS ─────────────────────────────────────────────────────────────────

elif seccion == "Análisis":
    st.header("📈 Análisis")
    dv = get_viajes()
    dg = get_gastos()
    dc = get_cxc()

    # Utilidad por semana
    st.subheader("📅 Utilidad por Semana")
    if not dv.empty and "fecha_salida" in dv.columns and "utilidad_viaje" in dv.columns:
        dv2 = dv.copy()
        dv2["fecha_salida"] = pd.to_datetime(dv2["fecha_salida"], errors="coerce")
        dv2["semana"] = dv2["fecha_salida"].dt.to_period("W").astype(str)
        semanal = dv2.groupby("semana")["utilidad_viaje"].apply(lambda x: x.apply(_num).sum()).reset_index()
        semanal.columns = ["Semana","Utilidad"]
        st.line_chart(semanal.set_index("Semana"))
    else:
        st.info("Sin datos suficientes para gráfica de utilidad.")

    st.divider()

    # Top 5 clientes
    st.subheader("🏆 Top 5 Clientes por Venta")
    if not dv.empty and "cliente" in dv.columns:
        top = dv.groupby("cliente").agg(
            Viajes=("folio","count"),
            Venta_Total=("precio_venta_viaje","sum"),
        ).reset_index().sort_values("Venta_Total", ascending=False).head(5)
        if not dc.empty and "cliente" in dc.columns:
            cobrado = dc.groupby("cliente")["monto_pagado"].sum().apply(_num).reset_index()
            cobrado.columns = ["cliente","Cobrado"]
            top = top.merge(cobrado, on="cliente", how="left")
            top["Saldo"] = (top["Venta_Total"] - top["Cobrado"]).apply(_fmt)
            top["Cobrado"] = top["Cobrado"].apply(_fmt)
        top["Venta_Total"] = top["Venta_Total"].apply(_fmt)
        st.dataframe(top, use_container_width=True, hide_index=True)

    st.divider()

    # Rentabilidad por chofer
    st.subheader("👷 Rentabilidad por Chofer")
    if not dv.empty and "chofer" in dv.columns:
        rv = dv.groupby("chofer").agg(
            Viajes=("folio","count"),
            Utilidad_Viajes=("utilidad_viaje","sum"),
        ).reset_index()
        if not dg.empty and "chofer" in dg.columns:
            rg = dg.groupby("chofer")["monto_gasto"].sum().apply(_num).reset_index()
            rg.columns = ["chofer","Gastos"]
            rv = rv.merge(rg, on="chofer", how="left").fillna(0)
            rv["Utilidad_Neta"] = (rv["Utilidad_Viajes"] - rv["Gastos"]).apply(_fmt)
            rv["Gastos"] = rv["Gastos"].apply(_fmt)
        rv["Utilidad_Viajes"] = rv["Utilidad_Viajes"].apply(_fmt)
        st.dataframe(rv, use_container_width=True, hide_index=True)

    st.divider()

    # Gastos por tipo
    st.subheader("📋 Gastos por Tipo")
    if not dg.empty and "tipo_gasto" in dg.columns and "monto_gasto" in dg.columns:
        total_g = dg["monto_gasto"].apply(_num).sum()
        grp = dg.groupby("tipo_gasto").agg(Cantidad=("folio","count"), Monto=("monto_gasto","sum")).reset_index()
        grp["Porcentaje"] = grp["Monto"].apply(lambda x: f"{_num(x)/total_g*100:.1f}%" if total_g else "0%")
        grp["Monto"] = grp["Monto"].apply(_fmt)
        st.dataframe(grp, use_container_width=True, hide_index=True)

    st.divider()

    # Viajes sin gastos
    st.subheader("⚠️ Viajes sin Gastos Registrados")
    if not dv.empty and not dg.empty and "folio" in dv.columns and "numero_viaje" in dg.columns:
        folios_con_gasto = set(dg["numero_viaje"].dropna().unique())
        sin_gastos = dv[~dv["folio"].isin(folios_con_gasto)]
        if sin_gastos.empty:
            st.success("Todos los viajes tienen gastos registrados.")
        else:
            cols = [c for c in ["folio","cliente","origen","destino","fecha_salida","estatus_viaje"] if c in sin_gastos.columns]
            st.dataframe(sin_gastos[cols], use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos suficientes.")

    st.divider()

    # Gastos sin viaje
    st.subheader("⚠️ Gastos sin Viaje Asociado")
    if not dg.empty and "numero_viaje" in dg.columns:
        sin_viaje = dg[dg["numero_viaje"].isna() | (dg["numero_viaje"] == "")]
        if sin_viaje.empty:
            st.success("Todos los gastos tienen viaje asociado.")
        else:
            cols = [c for c in ["folio","fecha_gasto","concepto","monto_gasto","tipo_gasto","chofer"] if c in sin_viaje.columns]
            st.dataframe(sin_viaje[cols], use_container_width=True, hide_index=True)
