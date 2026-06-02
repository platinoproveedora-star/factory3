"""
Dashboard Empresarial — COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV
Proyecto: PROY-001 · Gastos operativos · v0.4.0
"""
from __future__ import annotations
import io
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import (
    apply_filters,
    delete_gasto,
    get_all_gastos,
    get_categorias,
    get_categoria_id_map,
    get_gastos_mes,
    get_meses_disponibles,
    get_usuario_id_map,
    get_usuarios,
    insert_gasto,
    patch_gasto,
    periodo_dates,
    prev_period,
)

try:
    from fpdf import FPDF
    _PDF_OK = True
except ImportError:
    _PDF_OK = False

st.set_page_config(
    page_title="Duralon — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth ─────────────────────────────────────────────────────────────────────

def _check_auth() -> bool:
    if st.session_state.get("authenticated"):
        return True
    st.markdown("## 🔒 Duralon — Acceso")
    pwd = st.text_input("Contraseña", type="password", key="pwd_input")
    if st.button("Entrar", type="primary"):
        expected = st.secrets.get("APP_PASSWORD", "") or st.secrets.get("app_password", "")
        if pwd and pwd == expected:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    return False

if not _check_auth():
    st.stop()

# ── Estilos ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.kpi { background:#1e293b; border-radius:10px; padding:18px 12px; text-align:center; color:#fff; }
.kpi h2 { margin:0; font-size:1.8rem; color:#38bdf8; }
.kpi p  { margin:2px 0 0; color:#94a3b8; font-size:.8rem; }
.kpi small { color:#f59e0b; font-size:.75rem; }
.kpi-sm h2 { font-size:1.3rem !important; }
.alert-warn { background:#7c3aed22; border-left:3px solid #7c3aed;
              padding:8px 12px; border-radius:4px; color:#c4b5fd; font-size:.85rem; }
.alert-ok   { background:#06966422; border-left:3px solid #069664;
              padding:8px 12px; border-radius:4px; color:#6ee7b7; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar / filtros ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Duralon Gastos")
    st.caption("Comercializadora Duralon de Chiapas SA de CV")
    st.divider()
    st.subheader("🔍 Filtros")
    st.caption("Aplican a Análisis, Detalle y Exportar")

    periodo_opts = ["Este mes", "Mes anterior", "Esta semana", "Hoy",
                    "Últimos 3 meses", "Este año", "Todo", "Personalizado"]
    periodo_sel  = st.selectbox("Período", periodo_opts)

    custom_desde = custom_hasta = None
    if periodo_sel == "Personalizado":
        custom_desde = st.date_input("Desde", date.today().replace(day=1))
        custom_hasta = st.date_input("Hasta", date.today())

    fecha_desde, fecha_hasta = periodo_dates(periodo_sel, custom_desde, custom_hasta)
    periodo_str = (
        f"{fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}"
        if fecha_desde and fecha_hasta else "Todo el historial"
    )

    all_cats  = get_categorias()
    cats_sel  = st.multiselect("Categorías", all_cats, default=all_cats)

    all_users  = [u["nombre"] for u in get_usuarios()]
    users_sel  = st.multiselect("Usuarios", all_users, default=all_users)

    col_mn, col_mx = st.columns(2)
    monto_min = col_mn.number_input("Monto mín.", 0.0, step=100.0)
    monto_max = col_mx.number_input("Monto máx.", 9_999_999.0, step=1_000.0)

    metodo_opts = ["Todos", "manual", "ai_ocr", "dashboard"]
    metodo_sel  = st.selectbox("Método captura", metodo_opts)

    st.divider()
    if st.button("🔄 Refrescar datos"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Cerrar sesión"):
        st.session_state["authenticated"] = False
        st.rerun()

# ── Datos globales ────────────────────────────────────────────────────────────
df_all_raw = get_all_gastos()

df_all = df_all_raw.copy()
if metodo_sel != "Todos" and not df_all.empty and "metodo_captura" in df_all.columns:
    df_all = df_all[df_all["metodo_captura"] == metodo_sel]

df = apply_filters(df_all, fecha_desde, fecha_hasta, cats_sel, users_sel, monto_min, monto_max)
f_prev_desde, f_prev_hasta = prev_period(fecha_desde, fecha_hasta)
df_prev = apply_filters(df_all, f_prev_desde, f_prev_hasta, cats_sel, users_sel, monto_min, monto_max)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Dashboard de Gastos — Duralon")
st.caption(
    f"Filtros activos: **{periodo_str}** · {len(df)} movimientos filtrados"
    f"  |  Total histórico: {len(df_all_raw)} gastos"
)
st.divider()

tab_ov, tab_mes, tab_anal, tab_det, tab_exp = st.tabs([
    "📊 Overview", "📅 Gastos del Mes", "📈 Análisis", "📋 Detalle", "📄 Exportar",
])

# ===========================================================================
# TAB 1 — OVERVIEW
# ===========================================================================
with tab_ov:
    df_ov = df_all_raw

    total_ov = df_ov["monto"].sum()      if not df_ov.empty else 0.0
    num_ov   = len(df_ov)
    prom_ov  = total_ov / num_ov         if num_ov > 0 else 0.0

    hoy         = date.today()
    mes_a       = df_ov[df_ov["fecha"].dt.month == hoy.month] if not df_ov.empty else pd.DataFrame()
    total_mes_a = mes_a["monto"].sum()   if not mes_a.empty else 0.0
    mes_ant_d   = hoy.replace(day=1) - timedelta(days=1)
    mes_b       = df_ov[df_ov["fecha"].dt.month == mes_ant_d.month] if not df_ov.empty else pd.DataFrame()
    total_mes_b = mes_b["monto"].sum()   if not mes_b.empty else 0.0
    var_meses   = ((total_mes_a - total_mes_b) / total_mes_b * 100) if total_mes_b > 0 else 0.0

    top_cat   = df_ov.groupby("categoria")["monto"].sum().idxmax()       if not df_ov.empty else "—"
    top_cat_v = df_ov.groupby("categoria")["monto"].sum().max()           if not df_ov.empty else 0.0
    top_usr   = df_ov.groupby("nombre_usuario")["monto"].sum().idxmax()  if not df_ov.empty and "nombre_usuario" in df_ov.columns else "—"
    top_usr_v = df_ov.groupby("nombre_usuario")["monto"].sum().max()     if not df_ov.empty and "nombre_usuario" in df_ov.columns else 0.0

    if not df_ov.empty:
        mayor_row = df_ov.loc[df_ov["monto"].idxmax()]
        mayor_txt = f"${mayor_row['monto']:,.0f}"
        mayor_det = str(mayor_row.get("categoria", ""))
    else:
        mayor_txt, mayor_det = "—", ""

    var_sign = "▲" if var_meses > 0 else ("▼" if var_meses < 0 else "—")

    st.subheader("Resumen global (todo el historial)")
    kpi_cols = st.columns(4)
    for col, (label, val, sub) in zip(kpi_cols, [
        ("💰 Total histórico",  f"${total_ov:,.0f}",    f"{num_ov} movimientos"),
        ("📅 Mes actual",        f"${total_mes_a:,.0f}", f"{var_sign} {abs(var_meses):.1f}% vs mes ant."),
        ("📐 Promedio/gasto",    f"${prom_ov:,.0f}",     "todo el tiempo"),
        ("🏆 Top categoría",     top_cat,                f"${top_cat_v:,.0f}"),
    ]):
        with col:
            st.markdown(f'<div class="kpi"><p>{label}</p><h2>{val}</h2><small>{sub}</small></div>', unsafe_allow_html=True)

    st.markdown("")
    kpi_cols2 = st.columns(4)
    for col, (label, val, sub) in zip(kpi_cols2, [
        ("👤 Top usuario",        top_usr,    f"${top_usr_v:,.0f}"),
        ("💎 Mayor gasto único",  mayor_txt,  mayor_det),
        ("🗓️ Categorías activas", str(df_ov["categoria"].nunique()) if not df_ov.empty else "0", "en todo el historial"),
        ("👥 Usuarios activos",   str(df_ov["nombre_usuario"].nunique()) if not df_ov.empty else "0", "registrados"),
    ]):
        with col:
            st.markdown(f'<div class="kpi kpi-sm"><p>{label}</p><h2>{val}</h2><small>{sub}</small></div>', unsafe_allow_html=True)

    st.divider()

    if not df_ov.empty:
        st.subheader("Por categoría — todo el historial")
        cat_summary = (
            df_ov.groupby("categoria")["monto"]
            .agg(["sum", "count", "mean"])
            .rename(columns={"sum": "Total ($)", "count": "Movimientos", "mean": "Promedio ($)"})
            .sort_values("Total ($)", ascending=False)
        )
        cat_summary["% total"]     = (cat_summary["Total ($)"] / total_ov * 100).round(1).astype(str) + "%"
        cat_summary["Total ($)"]   = cat_summary["Total ($)"].map("${:,.0f}".format)
        cat_summary["Promedio ($)"] = cat_summary["Promedio ($)"].map("${:,.0f}".format)
        st.dataframe(cat_summary, use_container_width=True)

        st.subheader("Distribución por categoría")
        cat_q = df_ov.groupby("categoria")["monto"].sum().sort_values(ascending=True).reset_index()
        fig = px.bar(cat_q, x="monto", y="categoria", orientation="h",
                     color="monto", color_continuous_scale="Blues",
                     labels={"monto": "Total ($)", "categoria": ""})
        fig.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                          font_color="white", coloraxis_showscale=False,
                          height=320, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Alertas")
    alertas = []
    if all_cats and not df_ov.empty:
        cats_sin_uso = [c for c in all_cats if c not in df_ov["categoria"].values]
        if cats_sin_uso:
            alertas.append(("⚠️", f"Categorías sin ningún movimiento: {', '.join(cats_sin_uso)}"))
    if not df_ov.empty and prom_ov > 0:
        for _, row in df_ov[df_ov["monto"] > prom_ov * 5].head(3).iterrows():
            alertas.append(("🔴", f"Gasto inusual: {row.get('folio','')} — ${row['monto']:,.0f} en {row.get('categoria','')}"))
    if not alertas:
        st.markdown('<div class="alert-ok">✅ Sin alertas.</div>', unsafe_allow_html=True)
    else:
        for icon, msg in alertas:
            st.markdown(f'<div class="alert-warn">{icon} {msg}</div>', unsafe_allow_html=True)
            st.markdown("")


# ===========================================================================
# TAB 2 — GASTOS DEL MES
# ===========================================================================
with tab_mes:
    st.subheader("📅 Gastos del Mes")
    MESES_ES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
                7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

    hoy = date.today()
    col_m, col_a, col_btn, _ = st.columns([2, 1, 1, 3])
    mes_num = col_m.selectbox("Mes", options=list(range(1,13)), index=hoy.month-1,
                               format_func=lambda m: MESES_ES[m])
    ano_sel = col_a.number_input("Año", min_value=2020, max_value=2035, value=hoy.year, step=1)
    if col_btn.button("🔄 Recargar", key="reload_mes"):
        st.session_state.pop("_mes_key", None)

    mes_key = f"{ano_sel}_{mes_num}"
    if st.session_state.get("_mes_key") != mes_key:
        st.session_state["_mes_key"]  = mes_key
        st.session_state["_mes_orig"] = get_gastos_mes(ano_sel, mes_num)

    df_mes_orig: pd.DataFrame = st.session_state["_mes_orig"]

    total_mes = df_mes_orig["monto"].sum()    if not df_mes_orig.empty else 0.0
    num_mes   = len(df_mes_orig)
    prom_mes  = total_mes / num_mes           if num_mes > 0 else 0.0
    top_c_mes = (df_mes_orig.groupby("categoria")["monto"].sum().idxmax() if not df_mes_orig.empty else "—")
    top_c_mes_v = (df_mes_orig.groupby("categoria")["monto"].sum().max() if not df_mes_orig.empty else 0.0)
    top_u_mes = (df_mes_orig.groupby("nombre_usuario")["monto"].sum().idxmax()
                 if not df_mes_orig.empty and "nombre_usuario" in df_mes_orig.columns else "—")
    ocr_cnt   = (df_mes_orig[df_mes_orig["metodo_captura"] == "ai_ocr"].shape[0] if not df_mes_orig.empty else 0)

    st.markdown(f"##### {MESES_ES[mes_num]} {ano_sel}")
    for col, (label, val, sub) in zip(st.columns(4), [
        ("💰 Total del mes",  f"${total_mes:,.0f}",  f"{num_mes} gastos"),
        ("📐 Promedio/gasto", f"${prom_mes:,.0f}",   ""),
        ("🏆 Top categoría",  top_c_mes,              f"${top_c_mes_v:,.0f}"),
        ("👤 Top usuario",    top_u_mes,              f"📸 {ocr_cnt} por OCR"),
    ]):
        with col:
            st.markdown(f'<div class="kpi kpi-sm"><p>{label}</p><h2>{val}</h2><small>{sub}</small></div>', unsafe_allow_html=True)

    st.markdown("")
    st.info("✏️ Edita directamente en la tabla. Agrega filas con ＋. Haz clic en **💾 Guardar cambios** para confirmar.")

    cats_list  = get_categorias()
    users_list = [u["nombre"] for u in get_usuarios()]
    _empty_row = {"folio": "", "fecha": date(ano_sel, mes_num, 1),
                  "categoria": cats_list[0] if cats_list else "",
                  "nombre_usuario": users_list[0] if users_list else "",
                  "monto": 0.0, "descripcion": "", "metodo_captura": "dashboard"}

    col_cfg = {
        "folio":          st.column_config.TextColumn("Folio", disabled=True, width="small"),
        "fecha":          st.column_config.DateColumn("Fecha", format="DD/MM/YYYY", required=True),
        "categoria":      st.column_config.SelectboxColumn("Categoría", options=cats_list, required=True),
        "nombre_usuario": st.column_config.SelectboxColumn("Usuario", options=users_list, required=True),
        "monto":          st.column_config.NumberColumn("Monto ($)", format="$ %.2f", min_value=0.0, required=True),
        "descripcion":    st.column_config.TextColumn("Descripción", max_chars=200),
        "metodo_captura": st.column_config.TextColumn("Método", disabled=True, width="small"),
    }

    df_edited = st.data_editor(
        df_mes_orig.copy() if not df_mes_orig.empty else pd.DataFrame([_empty_row]),
        column_config=col_cfg, num_rows="dynamic",
        use_container_width=True, key=f"editor_{mes_key}", hide_index=True,
    )

    col_save, col_total_edit, _ = st.columns([2, 3, 4])
    total_edited = df_edited["monto"].sum() if not df_edited.empty else 0.0
    col_total_edit.markdown(
        f"**Total editado: ${total_edited:,.2f}**  "
        f"({'▲' if total_edited > total_mes else '▼'} ${abs(total_edited - total_mes):,.2f} vs cargado)"
        if num_mes > 0 else f"**Total: ${total_edited:,.2f}**"
    )

    if col_save.button("💾 Guardar cambios", type="primary", key="save_mes"):
        msgs: list[str] = []
        orig_folios = set(df_mes_orig["folio"].dropna().astype(str)) if not df_mes_orig.empty else set()
        edit_folios: set[str] = set()
        cat_map = get_categoria_id_map()
        usr_map = get_usuario_id_map()

        for _, row in df_edited.iterrows():
            folio = str(row.get("folio", "") or "").strip()
            if not folio or folio == "None":
                if not row.get("categoria") or not row.get("nombre_usuario"):
                    continue
                try:
                    monto_n = float(row["monto"])
                except Exception:
                    monto_n = 0.0
                if monto_n <= 0:
                    msgs.append("⚠️ Fila nueva sin monto válido, omitida.")
                    continue
                result = insert_gasto(
                    categoria=str(row["categoria"]),
                    usuario=str(row["nombre_usuario"]),
                    monto=monto_n,
                    fecha=row["fecha"] if isinstance(row["fecha"], date) else date(ano_sel, mes_num, 1),
                    descripcion=str(row.get("descripcion", "") or ""),
                )
                msgs.append(f"✅ Agregado {result['folio']}" if result.get("ok") else f"❌ {result.get('error')}")
            else:
                edit_folios.add(folio)
                if folio not in orig_folios:
                    continue
                orig_rows = df_mes_orig[df_mes_orig["folio"] == folio]
                if orig_rows.empty:
                    continue
                orig_row = orig_rows.iloc[0]
                patch: dict = {}
                new_cat = str(row.get("categoria", "") or "")
                if new_cat and new_cat != str(orig_row.get("categoria", "")):
                    cat_id = cat_map.get(new_cat)
                    if cat_id:
                        patch["categoria_id"] = cat_id
                new_usr = str(row.get("nombre_usuario", "") or "")
                if new_usr and new_usr != str(orig_row.get("nombre_usuario", "")):
                    usr_id = usr_map.get(new_usr)
                    if usr_id:
                        patch["usuario_id"] = usr_id
                try:
                    new_monto = float(row["monto"])
                except Exception:
                    new_monto = orig_row["monto"]
                if new_monto != float(orig_row["monto"]):
                    patch["monto"] = new_monto
                new_fecha = row.get("fecha")
                if new_fecha and str(new_fecha) != str(orig_row.get("fecha")):
                    patch["fecha"] = str(new_fecha)
                new_desc = str(row.get("descripcion", "") or "")
                if new_desc != str(orig_row.get("descripcion", "") or ""):
                    patch["descripcion"] = new_desc
                if patch:
                    msgs.append(f"✅ Actualizado {folio}" if patch_gasto(folio, patch) else f"❌ Error actualizando {folio}")

        for folio in orig_folios:
            if folio not in edit_folios:
                msgs.append(f"🗑️ Eliminado {folio}" if delete_gasto(folio) else f"❌ Error al eliminar {folio}")

        for m in msgs:
            st.write(m)
        if not msgs:
            st.success("Sin cambios que guardar.")
        st.session_state.pop("_mes_key", None)
        st.cache_data.clear()
        st.rerun()


# ===========================================================================
# TAB 3 — ANÁLISIS
# ===========================================================================
with tab_anal:
    st.caption(f"Filtros: {periodo_str} · {len(df)} movimientos")
    if df.empty:
        st.info("Sin datos para el período y filtros seleccionados.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Gasto por categoría")
            cat_d = df.groupby("categoria")["monto"].sum().sort_values().reset_index()
            fig1  = px.bar(cat_d, x="monto", y="categoria", orientation="h",
                           color="monto", color_continuous_scale="Blues",
                           labels={"monto": "Total ($)", "categoria": ""})
            fig1.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                               font_color="white", coloraxis_showscale=False,
                               margin=dict(l=0, r=0, t=5, b=0))
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            st.subheader("Gasto por usuario")
            usr_d = df.groupby("nombre_usuario")["monto"].sum().reset_index()
            fig2  = px.pie(usr_d, values="monto", names="nombre_usuario",
                           color_discrete_sequence=px.colors.sequential.Blues_r)
            fig2.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                               font_color="white", margin=dict(l=0, r=0, t=5, b=0))
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Tendencia mensual")
        df_t = df.copy()
        df_t["mes"] = df_t["fecha"].dt.to_period("M").astype(str)
        trend = df_t.groupby("mes")["monto"].agg(["sum", "count"]).reset_index()
        trend.columns = ["Mes", "Total ($)", "Movimientos"]
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=trend["Mes"], y=trend["Total ($)"], name="Total",
                              marker_color="#1e40af", opacity=0.6))
        fig3.add_trace(go.Scatter(x=trend["Mes"], y=trend["Total ($)"],
                                  mode="lines+markers", name="Tendencia",
                                  line=dict(color="#38bdf8", width=2)))
        fig3.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                            font_color="white", legend=dict(orientation="h"),
                            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
                            margin=dict(l=0, r=0, t=5, b=0))
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Mes actual vs anterior — por categoría")
        hoy_a        = date.today()
        mes_actual   = df[df["fecha"].dt.to_period("M") == pd.Period(hoy_a, "M")]
        mes_ant_f    = hoy_a.replace(day=1) - timedelta(days=1)
        mes_anterior = df[df["fecha"].dt.to_period("M") == pd.Period(mes_ant_f, "M")]
        if not mes_actual.empty or not mes_anterior.empty:
            comp = pd.concat([
                mes_actual.groupby("categoria")["monto"].sum().rename("Mes actual"),
                mes_anterior.groupby("categoria")["monto"].sum().rename("Mes anterior"),
            ], axis=1).fillna(0).reset_index()
            comp.columns = ["Categoria", "Mes actual", "Mes anterior"]
            fig4 = px.bar(comp, x="Categoria", y=["Mes actual", "Mes anterior"], barmode="group",
                          color_discrete_map={"Mes actual": "#38bdf8", "Mes anterior": "#475569"})
            fig4.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                               font_color="white", legend=dict(orientation="h"),
                               xaxis=dict(tickangle=-30), margin=dict(l=0, r=0, t=5, b=0))
            st.plotly_chart(fig4, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Top 5 gastos más altos")
            top5 = df.nlargest(5, "monto")[["folio","fecha","categoria","nombre_usuario","monto"]].copy()
            top5["fecha"] = top5["fecha"].dt.date
            top5["monto"] = top5["monto"].map("${:,.0f}".format)
            st.dataframe(top5, use_container_width=True, hide_index=True)
        with c4:
            st.subheader("Movimientos por día de semana")
            df_wd = df.copy()
            df_wd["dow"] = df_wd["fecha"].dt.day_name()
            order     = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            labels_es = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
                         "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}
            dow_d = df_wd.groupby("dow")["monto"].agg(["sum","count"]).reindex(order).fillna(0).reset_index()
            dow_d["dow"] = dow_d["dow"].map(labels_es)
            fig5 = px.bar(dow_d, x="dow", y="sum", text="count",
                          labels={"dow":"Día","sum":"Total ($)"},
                          color_discrete_sequence=["#3b82f6"])
            fig5.update_traces(texttemplate="%{text} movs", textposition="outside")
            fig5.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                               font_color="white", margin=dict(l=0, r=0, t=5, b=0))
            st.plotly_chart(fig5, use_container_width=True)


# ===========================================================================
# TAB 4 — DETALLE
# ===========================================================================
with tab_det:
    st.subheader(f"Detalle de gastos — {len(df)} registros")
    st.caption(f"Filtros activos: {periodo_str}")
    if df.empty:
        st.info("Sin datos para el período y filtros seleccionados.")
    else:
        busqueda = st.text_input("🔍 Buscar en descripción o folio")
        df_det   = df.copy()
        if busqueda:
            mask = (df_det["descripcion"].fillna("").str.contains(busqueda, case=False) |
                    df_det["folio"].fillna("").str.contains(busqueda, case=False))
            df_det = df_det[mask]
        co1, co2 = st.columns(2)
        sort_col = co1.selectbox("Ordenar por", ["fecha","monto","categoria","nombre_usuario"])
        sort_asc = co2.checkbox("Ascendente", value=False)
        df_det   = df_det.sort_values(sort_col, ascending=sort_asc)
        display_cols = [c for c in ["folio","fecha","categoria","nombre_usuario",
                                    "monto","descripcion","metodo_captura"] if c in df_det.columns]
        df_show = df_det[display_cols].copy()
        df_show["fecha"] = df_show["fecha"].dt.date
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        c_tot1, c_tot2, c_tot3 = st.columns(3)
        c_tot1.metric("Total mostrado", f"${df_det['monto'].sum():,.0f}")
        c_tot2.metric("Registros",      str(len(df_det)))
        c_tot3.metric("Promedio",       f"${df_det['monto'].mean():,.0f}" if len(df_det) else "$0")


# ===========================================================================
# TAB 5 — EXPORTAR
# ===========================================================================
with tab_exp:
    st.subheader("📥 Exportar Excel")
    exp_cols_opts = [c for c in ["folio","fecha","categoria","nombre_usuario",
                                  "monto","descripcion","metodo_captura"] if c in df.columns]
    exp_cols_sel  = st.multiselect("Columnas a incluir", exp_cols_opts, default=exp_cols_opts)
    inc_resumen   = st.checkbox("Incluir hoja de resumen por categoría", value=True)

    if not df.empty:
        buf = io.BytesIO()
        df_exp = df[exp_cols_sel].copy() if exp_cols_sel else df.copy()
        if "fecha" in df_exp.columns:
            df_exp["fecha"] = df_exp["fecha"].dt.date
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_exp.to_excel(writer, index=False, sheet_name="Gastos")
            if inc_resumen and not df.empty:
                resumen = df.groupby("categoria")["monto"].agg(["sum","count","mean"])
                resumen.columns = ["Total","Movimientos","Promedio"]
                resumen.to_excel(writer, sheet_name="Por Categoría")
        st.download_button(
            label="⬇️ Descargar Excel",
            data=buf.getvalue(),
            file_name=f"duralon_gastos_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning("Sin datos para exportar con los filtros actuales.")

st.divider()
st.caption("Duralon Gastos v0.4.0 · PROY-001 · proy001dash2")
