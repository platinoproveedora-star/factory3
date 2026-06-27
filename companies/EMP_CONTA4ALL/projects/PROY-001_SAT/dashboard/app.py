"""Conta4all SAT — Dashboard de CFDIs (Sincronizar / Solicitudes / Ingresos / Egresos)."""
from __future__ import annotations

import base64
import calendar
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Entorno ───────────────────────────────────────────────────────────────────
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            if _k.strip() not in os.environ:
                os.environ[_k.strip()] = _v.strip()

import streamlit as st

st.set_page_config(
    page_title="Conta4all SAT",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SkillRunner ───────────────────────────────────────────────────────────────
def _run_skill(nombre: str, context: dict) -> dict:
    _root = str(Path(__file__).resolve().parents[5])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from factory.engine import SkillLoader, SkillRunner
    _base = Path(_root) / "factory"
    ext   = _base / "skills" / "externos"
    ext.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(internal_root=_base / "skills" / "internos", external_root=ext)
    return SkillRunner(loader).run(nombre, context)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _context_base(extra: dict | None = None) -> dict:
    ctx = {
        "company_id":   os.getenv("COMPANY_ID", "EMP_CONTA4ALL"),
        "project_code": os.getenv("PROJECT_CODE", "PROY-001"),
        "schema":       os.getenv("SUPABASE_SCHEMA", "uc102_proy001"),
        "dry_run":      False,
    }
    if extra:
        ctx.update(extra)
    return ctx


def _today_mx() -> date:
    return datetime.now(ZoneInfo("America/Mexico_City")).date()


def _particion_rangos(fi: str, ff: str) -> list[tuple[str, str]]:
    d_ini = datetime.strptime(fi, "%Y-%m-%d").date()
    d_fin = datetime.strptime(ff, "%Y-%m-%d").date()
    rangos, cur = [], d_ini
    while cur <= d_fin:
        mes_fin = cur.month + 11
        yr_fin  = cur.year + (mes_fin - 1) // 12
        mes_fin = ((mes_fin - 1) % 12) + 1
        fin_periodo  = date(yr_fin, mes_fin, calendar.monthrange(yr_fin, mes_fin)[1])
        fin_efectivo = min(fin_periodo, d_fin)
        rangos.append((cur.strftime("%Y-%m-%d"), fin_efectivo.strftime("%Y-%m-%d")))
        cur = fin_efectivo + timedelta(days=1)
        if cur > d_fin:
            break
    return rangos or [(fi, ff)]


def _remember_request(label: str, payload: dict) -> None:
    st.session_state.setdefault("sat_requests", [])
    signature = (payload.get("tipo", ""), payload.get("tipo_solicitud", ""),
                 payload.get("fecha_inicio", ""), payload.get("fecha_fin", ""),
                 payload.get("rfc_contraparte", ""))
    duplicate = any(
        (r.get("tipo",""), r.get("tipo_solicitud",""), r.get("fecha_inicio",""),
         r.get("fecha_fin",""), r.get("rfc_contraparte","")) == signature
        for r in st.session_state["sat_requests"]
    )
    st.session_state["sat_requests"].insert(0, {
        "label": label, "estado_local": "Aceptada",
        "duplicada_local": "Si" if duplicate else "",
        "ultimo_resultado": "", **payload,
    })
    st.session_state["sat_requests"] = st.session_state["sat_requests"][:12]


def _update_request(index: int, values: dict) -> None:
    rows = st.session_state.get("sat_requests", [])
    if 0 <= index < len(rows):
        rows[index].update(values)


_MESES_ES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
             7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

_COL_CFG = {
    "total":    st.column_config.NumberColumn("Total",    format="$%.2f"),
    "subtotal": st.column_config.NumberColumn("Subtotal", format="$%.2f"),
    "descuento":st.column_config.NumberColumn("Descuento",format="$%.2f"),
}


def _cfdi_meses(cfdis: list, cols_display: list[str], search: str) -> None:
    """Tabla de CFDIs agrupada por mes con expanders colapsables."""
    import pandas as pd

    if not cfdis:
        st.info("Sin CFDIs para los filtros seleccionados.")
        return

    df = pd.DataFrame(cfdis)

    if search.strip():
        mask = df.apply(
            lambda col: col.astype(str).str.contains(search.strip(), case=False, na=False)
        ).any(axis=1)
        df = df[mask]
        if df.empty:
            st.info(f"Sin resultados para '{search}'.")
            return

    cols = [c for c in cols_display if c in df.columns]

    total_gral = df["total"].astype(float).sum() if "total" in df.columns else 0
    st.caption(f"{len(df)} registros  —  Total: **${total_gral:,.2f}**")

    csv = df[cols].to_csv(index=False).encode("utf-8") if cols else df.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar CSV completo", csv, "cfdis.csv", "text/csv")

    # Agrupar por año-mes
    if "fecha_emision" in df.columns:
        df["_f"] = pd.to_datetime(df["fecha_emision"], errors="coerce")
        df["_y"] = df["_f"].dt.year.fillna(0).astype(int)
        df["_m"] = df["_f"].dt.month.fillna(0).astype(int)
        df = df.sort_values("_f", ascending=False)

        for (anio, mes), grupo in df.groupby(["_y", "_m"], sort=False):
            total_mes = grupo["total"].astype(float).sum() if "total" in grupo.columns else 0
            mes_txt   = _MESES_ES.get(mes, str(mes))
            header    = f"{mes_txt} {anio}  —  {len(grupo)} facturas  —  ${total_mes:,.2f}"
            with st.expander(header, expanded=False):
                df_show = grupo[cols].drop(columns=["_f","_y","_m"], errors="ignore") if cols else grupo
                st.dataframe(df_show, use_container_width=True, hide_index=True, column_config=_COL_CFG)
    else:
        df_show = df[cols] if cols else df
        st.dataframe(df_show, use_container_width=True, hide_index=True, column_config=_COL_CFG)


# ══════════════════════════════════════════════════════════════════════════════
# Cargar empresas configuradas en env vars
# Formato: EMPRESA_1_RFC, EMPRESA_1_CER_B64, EMPRESA_1_KEY_B64, EMPRESA_1_PWD
#          EMPRESA_2_RFC, ...  hasta EMPRESA_9
# ══════════════════════════════════════════════════════════════════════════════
def _empresas_configuradas() -> list[dict]:
    empresas = []
    for i in range(1, 10):
        rfc = os.getenv(f"EMPRESA_{i}_RFC", "").strip()
        if not rfc:
            break
        empresas.append({
            "idx":     i,
            "rfc":     rfc,
            "label":   os.getenv(f"EMPRESA_{i}_LABEL", rfc),
            "cer_b64": os.getenv(f"EMPRESA_{i}_CER_B64", ""),
            "key_b64": os.getenv(f"EMPRESA_{i}_KEY_B64", ""),
            "pwd":     os.getenv(f"EMPRESA_{i}_PWD", ""),
        })
    # fallback: empresa única con variables genéricas
    if not empresas:
        rfc = os.getenv("SAT_RFC", "").strip()
        if rfc:
            empresas.append({
                "idx": 1, "rfc": rfc, "label": rfc,
                "cer_b64": os.getenv("SAT_EFIRMA_CER_B64", ""),
                "key_b64": os.getenv("SAT_EFIRMA_KEY_B64", ""),
                "pwd":     os.getenv("SAT_EFIRMA_PASSWORD", ""),
            })
    return empresas


_EMPRESAS = _empresas_configuradas()


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🧾 Conta4all SAT")

    # Selector de empresa si hay varias configuradas
    if _EMPRESAS:
        emp_labels = [f"{e['label']}" for e in _EMPRESAS]
        emp_idx = st.selectbox("Empresa", range(len(_EMPRESAS)),
                               format_func=lambda i: emp_labels[i],
                               key="sidebar_empresa")
        _EMP_SEL = _EMPRESAS[emp_idx]
    else:
        _EMP_SEL = None

    st.divider()
    page = st.radio(
        "Sección",
        ["Sincronizar", "Solicitudes", "Ingresos", "Egresos"],
        label_visibility="collapsed",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sincronizar
# ══════════════════════════════════════════════════════════════════════════════
if page == "Sincronizar":
    st.title("Sincronizar con SAT")

    # ── Credenciales: env vars o upload manual ────────────────────────────────
    with st.container(border=True):
        st.subheader("e.firma")

        _env_rfc     = _EMP_SEL["rfc"]     if _EMP_SEL else ""
        _env_cer_b64 = _EMP_SEL["cer_b64"] if _EMP_SEL else ""
        _env_key_b64 = _EMP_SEL["key_b64"] if _EMP_SEL else ""
        _env_pwd     = _EMP_SEL["pwd"]     if _EMP_SEL else ""

        _creds_desde_env = bool(_env_cer_b64 and _env_key_b64)

        if _creds_desde_env:
            st.success(f"e.firma configurada en Render: **{_env_rfc}**")
            rfc    = _env_rfc
            cer_up = None
            key_up = None
            if _env_pwd:
                password = _env_pwd
                st.caption("Contraseña cargada desde configuración.")
            else:
                password = st.text_input("Contraseña de la e.firma", type="password",
                                         key="sync_pwd",
                                         help="No está en env vars — escríbela aquí.")
        else:
            st.info("Sube tu e.firma o configura las env vars en Render para no tener que subir los archivos cada vez.")
            col1, col2, col3 = st.columns(3)
            rfc    = col1.text_input("RFC", value=_env_rfc, placeholder="XAXX010101000", key="sync_rfc")
            cer_up = col2.file_uploader("Certificado (.cer)", type=None, key="sync_cer")
            key_up = col3.file_uploader("Llave privada (.key)", type=None, key="sync_key")
            password = st.text_input("Contraseña de la e.firma", type="password",
                                     key="sync_pwd", help="La contraseña nunca se almacena.")

    if _creds_desde_env:
        creds_ok = bool(rfc and password)
    else:
        creds_ok = bool(rfc and cer_up and key_up and password)

    if not creds_ok:
        st.caption("Faltan credenciales para habilitar la sincronización.")

    st.divider()

    with st.container(border=True):
        st.subheader("Periodo")
        hoy    = _today_mx()
        primer = hoy.replace(day=1)
        col1, col2, col3 = st.columns(3)
        fi = col1.text_input("Fecha inicio", value=primer.strftime("%Y-%m-%d"), key="sync_fi")
        ff = col2.text_input("Fecha fin",    value=hoy.strftime("%Y-%m-%d"),    key="sync_ff")
        s_tc = col3.selectbox(
            "Tipo comprobante",
            ["", "I", "E", "T", "N", "P"],
            format_func=lambda x: {"": "Todos", "I": "Ingreso", "E": "Egreso",
                                   "T": "Traslado", "N": "Nomina", "P": "Pago"}.get(x, x),
            key="sync_tc",
        )
        rfc_contraparte = st.text_input(
            "RFC cliente/proveedor (opcional)",
            value="", key="sync_rfc_contraparte",
            help="RFC exacto. Para ingresos filtra receptor; para egresos filtra emisor.",
        ).strip().upper()

        try:
            rangos = _particion_rangos(fi, ff)
            if len(rangos) > 1:
                st.warning(f"El rango excede 12 meses — se descargará en **{len(rangos)} periodos**.")
        except Exception:
            rangos = [(fi, ff)]

    st.divider()

    col_a, col_b, col_c, col_d = st.columns(4)
    create_ing      = col_a.button("Solicitar ingresos",   disabled=not creds_ok, use_container_width=True)
    create_egr      = col_b.button("Solicitar egresos",    disabled=not creds_ok, use_container_width=True)
    create_meta_ing = col_c.button("Metadata ingresos",    disabled=not creds_ok, use_container_width=True)
    create_meta_egr = col_d.button("Metadata egresos",     disabled=not creds_ok, use_container_width=True)
    col_e, col_f    = st.columns(2)
    create_party_ing = col_e.button("Ingresos por cliente",   disabled=not creds_ok or not rfc_contraparte, use_container_width=True)
    create_party_egr = col_f.button("Egresos por proveedor",  disabled=not creds_ok or not rfc_contraparte, use_container_width=True)

    saved_verify_idx = None
    if st.session_state.get("sat_requests"):
        st.subheader("Solicitudes en esta sesión")
        head = st.columns([1.2, 0.7, 0.9, 1.2, 1.4, 2.7, 1.2, 1.1])
        for cap, h in zip(["Acción","Tipo","Solicitud","Periodo","RFC filtro","ID SAT","Estado",""], head):
            h.caption(cap)
        for idx, req_row in enumerate(st.session_state["sat_requests"]):
            cols = st.columns([1.2, 0.7, 0.9, 1.2, 1.4, 2.7, 1.2, 1.1])
            cols[0].write(req_row.get("label", ""))
            cols[1].write(req_row.get("tipo", ""))
            cols[2].write(req_row.get("tipo_solicitud", ""))
            cols[3].write(f"{req_row.get('fecha_inicio','')} → {req_row.get('fecha_fin','')}")
            cols[4].write(req_row.get("rfc_contraparte", "") or "Todos")
            cols[5].code(req_row.get("id_solicitud", "") or "-", language=None)
            estado = req_row.get("estado_local", "Aceptada")
            if req_row.get("duplicada_local"):
                estado += " / duplicada"
            if req_row.get("ultimo_resultado"):
                estado += f": {req_row.get('ultimo_resultado')}"
            cols[6].write(estado)
            if cols[7].button("Verificar", key=f"verify_saved_{idx}_{req_row.get('id_solicitud','')}",
                              disabled=not creds_ok or not req_row.get("id_solicitud"),
                              use_container_width=True):
                saved_verify_idx = idx

    existing_id = st.text_input("ID solicitud SAT existente", value="", key="sync_id_solicitud")
    col_g, col_h = st.columns(2)
    verify_ing = col_g.button("Verificar/descargar ingresos", type="primary",
                               disabled=not creds_ok or not existing_id.strip(), use_container_width=True)
    verify_egr = col_h.button("Verificar/descargar egresos", type="primary",
                               disabled=not creds_ok or not existing_id.strip(), use_container_width=True)

    create_any = any([create_ing, create_egr, create_meta_ing, create_meta_egr, create_party_ing, create_party_egr])
    verify_any = verify_ing or verify_egr or saved_verify_idx is not None

    if create_any or verify_any:
        # Resolver cer_b64 / key_b64 desde env vars o desde archivos subidos
        if _creds_desde_env:
            if not rfc or not password:
                st.error("Falta RFC o contraseña.")
                st.stop()
            cer_b64 = _env_cer_b64
            key_b64 = _env_key_b64
        else:
            if not all([rfc, cer_up, key_up, password]):
                st.error("Vuelve a subir el .cer, .key y confirma la contraseña.")
                st.stop()
            cer_bytes = cer_up.getvalue()
            key_bytes = key_up.getvalue()
            if not cer_bytes or not key_bytes:
                st.error("Los archivos llegaron vacíos. Vuelve a subirlos.")
                st.stop()
            cer_b64 = base64.b64encode(cer_bytes).decode()
            key_b64 = base64.b64encode(key_bytes).decode()

        rfc = rfc.strip().upper()
        common_ctx = _context_base({
            "rfc": rfc, "empresa_id": rfc, "rfc_propietario": rfc,
            "cer_b64": cer_b64, "key_b64": key_b64, "key_password": password,
            "fecha_inicio": fi, "fecha_fin": ff, "tipo_comprobante": s_tc,
        })

        if create_any:
            request_type = "Metadata" if (create_meta_ing or create_meta_egr) else "CFDI"
            target_tipo  = "R" if (create_egr or create_meta_egr or create_party_egr) else "E"
            label = {
                (True,  False, False, False, False, False): "Ingresos",
                (False, True,  False, False, False, False): "Egresos",
                (False, False, True,  False, False, False): "Metadata ingresos",
                (False, False, False, True,  False, False): "Metadata egresos",
                (False, False, False, False, True,  False): "Ingresos por cliente",
                (False, False, False, False, False, True ): "Egresos por proveedor",
            }.get((create_ing, create_egr, create_meta_ing, create_meta_egr, create_party_ing, create_party_egr), "Solicitud")
            use_party = create_party_ing or create_party_egr

            with st.spinner(f"Creando solicitud SAT: {label}..."):
                auth = _run_skill("vertical_sat/sat_auth", {**common_ctx, "dry_run": False})
                if not auth.get("ok"):
                    st.error(auth.get("error", "Error auth SAT"))
                    st.stop()
                req = _run_skill("vertical_sat/sat_cfdi_solicitud", {
                    **common_ctx, "token": auth["data"]["token"],
                    "tipo": target_tipo, "tipo_solicitud": request_type,
                    "rfc_contraparte": rfc_contraparte if use_party else "",
                    "dry_run": False,
                })

            if req.get("ok"):
                id_req = req.get("data", {}).get("id_solicitud", "")
                _remember_request(label, {
                    "tipo": target_tipo, "tipo_solicitud": request_type,
                    "fecha_inicio": fi, "fecha_fin": ff,
                    "tipo_comprobante": s_tc,
                    "rfc_contraparte": rfc_contraparte if use_party else "",
                    "id_solicitud": id_req,
                })
                st.success(f"{label}: solicitud aceptada")
                st.code(id_req)
            else:
                st.error(req.get("error", "Error solicitud SAT"))
            st.stop()

        if saved_verify_idx is not None:
            saved_req = st.session_state["sat_requests"][saved_verify_idx]
            lbl = f"{saved_req.get('label','Solicitud')} {saved_req.get('fecha_inicio','')}→{saved_req.get('fecha_fin','')}"
            with st.spinner(f"Verificando {lbl}..."):
                r = _run_skill("vertical_sat/sat_cfdi_sync", {
                    **common_ctx,
                    "fecha_inicio": saved_req.get("fecha_inicio", fi),
                    "fecha_fin":    saved_req.get("fecha_fin", ff),
                    "tipo":         saved_req.get("tipo", "E"),
                    "tipo_solicitud": saved_req.get("tipo_solicitud", "CFDI"),
                    "tipo_comprobante": saved_req.get("tipo_comprobante", s_tc),
                    "id_solicitud": saved_req.get("id_solicitud", ""),
                    "rfc_contraparte": saved_req.get("rfc_contraparte", ""),
                })
            if r.get("ok"):
                _update_request(saved_verify_idx, {"estado_local": "Verificada", "ultimo_resultado": r.get("message","OK")})
                st.success(f"{lbl}: {r.get('message','OK')}")
                for paso in r.get("data", {}).get("log", []):
                    icon = "✅" if paso.get("ok") else "❌"
                    st.caption(f"{icon} {paso['paso']} — {paso.get('msg','')}")
            else:
                err = r.get("error", "Error")
                _update_request(saved_verify_idx, {"estado_local": "Error", "ultimo_resultado": err})
                st.error(f"{lbl}: {err}")
            st.stop()

        tipos = ["R"] if verify_egr else ["E"]
        for t in tipos:
            for rango_fi, rango_ff in rangos:
                lbl = f"{t} — {rango_fi} → {rango_ff}"
                with st.spinner(f"Descargando {lbl}..."):
                    r = _run_skill("vertical_sat/sat_cfdi_sync", _context_base({
                        "rfc": rfc, "empresa_id": rfc, "rfc_propietario": rfc,
                        "cer_b64": cer_b64, "key_b64": key_b64, "key_password": password,
                        "fecha_inicio": rango_fi, "fecha_fin": rango_ff,
                        "tipo": t, "tipo_comprobante": s_tc,
                        "id_solicitud": existing_id.strip(),
                        "rfc_contraparte": rfc_contraparte,
                    }))
                if r.get("ok"):
                    st.success(f"{lbl}: {r.get('message','OK')}")
                    for paso in r.get("data", {}).get("log", []):
                        icon = "✅" if paso.get("ok") else "❌"
                        st.caption(f"{icon} {paso['paso']} — {paso.get('msg','')}")
                else:
                    st.error(f"{lbl}: {r.get('error','Error')}")


# ══════════════════════════════════════════════════════════════════════════════
# Solicitudes (guardadas en DB)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Solicitudes":
    import pandas as pd

    st.title("Solicitudes SAT guardadas")
    st.caption("Solicitudes persistidas en base de datos — sobreviven entre sesiones.")

    col1, col2 = st.columns(2)
    f_rfc  = col1.text_input("RFC", value=os.getenv("SAT_RFC", ""), key="sol_rfc")
    f_tipo = col2.selectbox("Tipo", ["Todos", "E (Ingresos)", "R (Egresos)"], key="sol_tipo")
    incl_vencidas = st.checkbox("Incluir vencidas", value=False, key="sol_venc")

    tipo_val = "" if f_tipo == "Todos" else f_tipo[0]
    ctx = _context_base({
        "action": "list",
        "empresa_id": f_rfc or os.getenv("COMPANY_ID", ""),
        "rfc": f_rfc,
    })
    if tipo_val:
        ctx["tipo"] = tipo_val
    if incl_vencidas:
        ctx["incluir_vencidas"] = True

    with st.spinner("Cargando solicitudes..."):
        r = _run_skill("vertical_sat/sat_solicitud_manager", ctx)

    _ESTADO_COLOR = {
        "Aceptada": "🟡", "En proceso": "🔵", "Terminada": "🟢",
        "Error": "🔴", "Rechazada": "🔴", "Vencida": "⚫", "Pendiente": "⚪",
    }

    if r.get("ok"):
        sols = r.get("data", {}).get("solicitudes", [])
        if not sols:
            st.info("No hay solicitudes guardadas para este RFC.")
        else:
            st.metric("Total solicitudes", len(sols))
            rows_display = []
            for s in sols:
                estado_txt = s.get("estado_txt", "?")
                rows_display.append({
                    "Estado":       f"{_ESTADO_COLOR.get(estado_txt,'⚪')} {estado_txt}",
                    "Tipo":         "Ingresos (E)" if s.get("tipo") == "E" else "Egresos (R)",
                    "Solicitud":    s.get("tipo_solicitud", ""),
                    "Periodo":      f"{s.get('fecha_inicio','')} → {s.get('fecha_fin','')}",
                    "CFDIs":        s.get("num_cfdis", 0),
                    "ID SAT":       s.get("id_solicitud", ""),
                    "Creada":       (s.get("created_at") or "")[:16].replace("T", " "),
                    "Actualizada":  (s.get("updated_at") or "")[:16].replace("T", " "),
                })
            df = pd.DataFrame(rows_display)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={"ID SAT": st.column_config.TextColumn(width="large")})

            st.divider()
            st.subheader("Reusar solicitud existente")
            st.caption("Copia el ID SAT de arriba y pégalo en la sección Sincronizar → campo 'ID solicitud SAT existente'.")
            for s in sols:
                if s.get("id_solicitud"):
                    estado_txt = s.get("estado_txt", "?")
                    label = (f"{_ESTADO_COLOR.get(estado_txt,'⚪')} "
                             f"{'E' if s.get('tipo')=='E' else 'R'} "
                             f"{s.get('fecha_inicio','')}→{s.get('fecha_fin','')} "
                             f"({s.get('num_cfdis',0)} CFDIs)")
                    st.code(s["id_solicitud"], language=None)
                    st.caption(label)
    else:
        st.error(r.get("error", "Error cargando solicitudes"))


# ══════════════════════════════════════════════════════════════════════════════
# Ingresos (E — emitidos por este RFC)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Ingresos":
    st.title("Ingresos — CFDIs emitidos")

    hoy     = _today_mx()
    enero_1 = date(hoy.year, 1, 1)
    rfc_env = (_EMP_SEL["rfc"] if _EMP_SEL else "") or os.getenv("SAT_RFC", "")

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        fi_ing = col1.text_input("Fecha inicio", value=enero_1.strftime("%Y-%m-%d"), key="ing_fi")
        ff_ing = col2.text_input("Fecha fin",    value=hoy.strftime("%Y-%m-%d"),     key="ing_ff")
        f_rfc  = col3.text_input("RFC propietario", value=rfc_env, key="ing_rfc")

        col4, col5 = st.columns([3, 1])
        buscar = col4.text_input("Buscar (nombre, RFC, UUID, cualquier campo...)", value="", key="ing_buscar",
                                  placeholder="ej: OXXO, PEMEX, uuid...")
        tc_ing = col5.selectbox("Tipo comprobante", ["Todos","I","E","T","N","P"],
                                 format_func=lambda x: {"Todos":"Todos","I":"Ingreso","E":"Egreso",
                                                        "T":"Traslado","N":"Nomina","P":"Pago"}.get(x,x),
                                 key="ing_tc")

    f_rfc = f_rfc.strip().upper()
    ctx = _context_base({
        "rfc_propietario": f_rfc, "empresa_id": f_rfc, "tipo": "E",
        "fecha_inicio": fi_ing, "fecha_fin": ff_ing, "limit": 5000,
    })

    with st.spinner("Cargando ingresos..."):
        r = _run_skill("vertical_sat/sat_cfdi_list", ctx)

    if not r.get("ok"):
        st.error(r.get("error", "Error"))
        st.stop()

    d     = r.get("data", {})
    cfdis = d.get("cfdis", [])
    if tc_ing != "Todos":
        cfdis = [c for c in cfdis if (c.get("tipo_comprobante") or "").upper() == tc_ing.upper()]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Facturas",         len(cfdis))
    m2.metric("Monto total",      "${:,.0f}".format(sum(float(c.get("total") or 0) for c in cfdis)))
    m3.metric("Tipo Ingreso (I)", sum(1 for c in cfdis if (c.get("tipo_comprobante") or "").upper() == "I"))
    m4.metric("Periodo",          f"{fi_ing} → {ff_ing}")

    _cfdi_meses(cfdis, cols_display=[
        "fecha_emision", "nombre_receptor", "rfc_receptor",
        "tipo_comprobante", "total", "subtotal", "descuento",
        "moneda", "forma_pago", "metodo_pago", "uso_cfdi", "uuid_cfdi",
    ], search=buscar)


# ══════════════════════════════════════════════════════════════════════════════
# Egresos (R — recibidos por este RFC)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Egresos":
    st.title("Egresos — CFDIs recibidos")

    hoy     = _today_mx()
    enero_1 = date(hoy.year, 1, 1)
    rfc_env = (_EMP_SEL["rfc"] if _EMP_SEL else "") or os.getenv("SAT_RFC", "")

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        fi_egr = col1.text_input("Fecha inicio", value=enero_1.strftime("%Y-%m-%d"), key="egr_fi")
        ff_egr = col2.text_input("Fecha fin",    value=hoy.strftime("%Y-%m-%d"),     key="egr_ff")
        f_rfc  = col3.text_input("RFC propietario", value=rfc_env, key="egr_rfc")

        col4, col5 = st.columns([3, 1])
        buscar = col4.text_input("Buscar (nombre, RFC, UUID, cualquier campo...)", value="", key="egr_buscar",
                                  placeholder="ej: TELMEX, SAT, uuid...")
        tc_egr = col5.selectbox("Tipo comprobante", ["Todos","I","E","T","N","P"],
                                 format_func=lambda x: {"Todos":"Todos","I":"Ingreso","E":"Egreso",
                                                        "T":"Traslado","N":"Nomina","P":"Pago"}.get(x,x),
                                 key="egr_tc")

    f_rfc = f_rfc.strip().upper()
    ctx = _context_base({
        "rfc_propietario": f_rfc, "empresa_id": f_rfc, "tipo": "R",
        "fecha_inicio": fi_egr, "fecha_fin": ff_egr, "limit": 5000,
    })

    with st.spinner("Cargando egresos..."):
        r = _run_skill("vertical_sat/sat_cfdi_list", ctx)

    if not r.get("ok"):
        st.error(r.get("error", "Error"))
        st.stop()

    d     = r.get("data", {})
    cfdis = d.get("cfdis", [])
    if tc_egr != "Todos":
        cfdis = [c for c in cfdis if (c.get("tipo_comprobante") or "").upper() == tc_egr.upper()]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Facturas",        len(cfdis))
    m2.metric("Monto total",     "${:,.0f}".format(sum(float(c.get("total") or 0) for c in cfdis)))
    m3.metric("Tipo Egreso (E)", sum(1 for c in cfdis if (c.get("tipo_comprobante") or "").upper() == "E"))
    m4.metric("Periodo",         f"{fi_egr} → {ff_egr}")

    _cfdi_meses(cfdis, cols_display=[
        "fecha_emision", "nombre_emisor", "rfc_emisor",
        "tipo_comprobante", "total", "subtotal", "descuento",
        "moneda", "forma_pago", "metodo_pago", "uso_cfdi", "uuid_cfdi",
    ], search=buscar)
