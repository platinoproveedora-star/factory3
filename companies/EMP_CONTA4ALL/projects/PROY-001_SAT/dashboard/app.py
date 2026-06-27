"""Conta4all SAT — Dashboard de CFDIs (Ingresos / Egresos) multi-RFC."""
from __future__ import annotations

import base64
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import calendar
from pathlib import Path

# ── Entorno ──────────────────────────────────────────────────────────────────
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
    initial_sidebar_state="collapsed",
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
def _particion_rangos(fi: str, ff: str) -> list[tuple[str, str]]:
    """Si el rango excede 12 meses, lo parte en periodos de hasta 12 meses."""
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


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🧾 Conta4all SAT")
    page = st.radio(
        "Sección",
        ["Sincronizar", "Ingresos", "Egresos"],
        label_visibility="collapsed",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sincronizar — credenciales + descarga en un solo paso
# ══════════════════════════════════════════════════════════════════════════════
if page == "Sincronizar":
    st.title("Sincronizar con SAT")

    st.info(
        "Sube tu **e.firma** (.cer y .key), escribe la contraseña y selecciona el periodo. "
        "Los archivos se usan solo para firmar la solicitud al SAT — **no se guardan en ningún lado**."
    )

    # ── Credenciales ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("e.firma")
        col1, col2, col3 = st.columns(3)

        rfc    = col1.text_input("RFC", value=os.getenv("SAT_RFC", ""), placeholder="XAXX010101000", key="sync_rfc")
        cer_up = col2.file_uploader("Certificado (.cer)", type=None, key="sync_cer")
        key_up = col3.file_uploader("Llave privada (.key)", type=None, key="sync_key")

        password = st.text_input(
            "Contraseña de la e.firma",
            type="password",
            key="sync_pwd",
            help="La contraseña nunca se almacena — se usa solo durante esta sesión.",
        )

    creds_ok = bool(rfc and cer_up and key_up and password)

    if not creds_ok:
        st.caption("Completa los 4 campos para habilitar la sincronización.")

    st.divider()

    # ── Parámetros de descarga ────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Periodo")
        hoy    = _today_mx()
        primer = hoy.replace(day=1)

        col1, col2, col3, col4 = st.columns(4)
        fi     = col1.text_input("Fecha inicio", value=primer.strftime("%Y-%m-%d"), key="sync_fi")
        ff     = col2.text_input("Fecha fin",    value=hoy.strftime("%Y-%m-%d"),    key="sync_ff")
        s_tipo = col3.selectbox(
            "Tipo",
            ["E", "R", "Ambos"],
            format_func=lambda x: {"E": "Ingresos (emitidos)", "R": "Egresos (recibidos)", "Ambos": "Ambos"}.get(x, x),
            key="sync_tipo",
        )
        s_tc = col4.selectbox(
            "Tipo comprobante",
            ["", "I", "E", "T", "N", "P"],
            format_func=lambda x: {"": "Todos", "I": "Ingreso", "E": "Egreso",
                                    "T": "Traslado", "N": "Nomina", "P": "Pago"}.get(x, x),
            key="sync_tc",
        )
        existing_id = st.text_input("ID solicitud SAT existente", value="", key="sync_id_solicitud")

        # Advertencia si rango > 12 meses
        try:
            rangos = _particion_rangos(fi, ff)
            if len(rangos) > 1:
                st.warning(
                    f"El rango excede 12 meses — se descargará en **{len(rangos)} periodos** automáticamente."
                )
        except Exception:
            rangos = [(fi, ff)]

    st.divider()

    # ── Botón sync ───────────────────────────────────────────────────────────
    if st.button("Sincronizar con SAT", type="primary", disabled=not creds_ok, use_container_width=True):
        if not all([rfc, cer_up, key_up, password]):
            st.error("Vuelve a subir el certificado .cer, la llave .key y confirma la contraseña.")
            st.stop()

        # Leer bytes de los archivos — en memoria, nunca a disco
        cer_bytes = cer_up.getvalue()
        key_bytes = key_up.getvalue()
        if not cer_bytes or not key_bytes:
            st.error("Los archivos de e.firma llegaron vacíos. Vuelve a subir el .cer y el .key.")
            st.stop()

        cer_b64 = base64.b64encode(cer_bytes).decode()
        key_b64 = base64.b64encode(key_bytes).decode()

        tipos = ["E", "R"] if s_tipo == "Ambos" else [s_tipo]

        for t in tipos:
            for rango_fi, rango_ff in rangos:
                lbl = f"{t} — {rango_fi} → {rango_ff}"
                with st.spinner(f"Descargando {lbl}..."):
                    r = _run_skill(
                        "vertical_sat/sat_cfdi_sync",
                        _context_base({
                            "rfc":              rfc,
                            "empresa_id":       rfc,
                            "rfc_propietario":  rfc,
                            "cer_b64":          cer_b64,
                            "key_b64":          key_b64,
                            "key_password":     password,
                            "fecha_inicio":     rango_fi,
                            "fecha_fin":        rango_ff,
                            "tipo":             t,
                            "tipo_comprobante": s_tc,
                            "id_solicitud":     existing_id.strip(),
                        }),
                    )

                if r.get("ok"):
                    st.success(f"{lbl}: {r.get('message', 'OK')}")
                    for paso in r.get("data", {}).get("log", []):
                        icon = "✅" if paso.get("ok") else "❌"
                        st.caption(f"{icon} {paso['paso']} — {paso.get('msg', '')}")
                else:
                    st.error(f"{lbl}: {r.get('error', 'Error')}")

        # Las variables cer_b64, key_b64, password salen de scope aquí — GC las descarta


# ══════════════════════════════════════════════════════════════════════════════
# Ingresos (E — emitidos)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Ingresos":
    import pandas as pd

    st.title("Ingresos — CFDIs emitidos")

    mes_actual = _today_mx().strftime("%Y-%m")
    col1, col2, col3 = st.columns(3)
    f_mes = col1.text_input("Mes (YYYY-MM)", value=mes_actual, key="ing_mes")
    f_dia = col2.text_input("Día específico YYYY-MM-DD (vacío = mes completo)", value="", key="ing_dia")
    f_rfc = col3.text_input("RFC", value=os.getenv("SAT_RFC", ""), key="ing_rfc")

    ctx = _context_base({"rfc_propietario": f_rfc, "empresa_id": f_rfc, "tipo": "E"})
    if f_dia.strip():
        ctx["dia"] = f_dia.strip()
    elif f_mes.strip():
        ctx["mes"] = f_mes.strip()

    with st.spinner("Cargando ingresos..."):
        r = _run_skill("vertical_sat/sat_cfdi_list", ctx)

    if r.get("ok"):
        d = r.get("data", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Total emitidos",    d.get("total", 0))
        m2.metric("Monto total",       "${:,.2f}".format(d.get("monto_total", 0)))
        m3.metric("Tipo Ingreso (I)",  d.get("total_ingresos", 0))
        cfdis = d.get("cfdis", [])
        if cfdis:
            df   = pd.DataFrame(cfdis)
            cols = [c for c in ["fecha_emision", "uuid_cfdi", "rfc_receptor", "nombre_receptor",
                                 "tipo_comprobante", "total", "moneda", "forma_pago", "estado"]
                    if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Sin CFDIs emitidos para este periodo.")
    else:
        st.caption("sat_cfdi_list no disponible — " + r.get("error", ""))


# ══════════════════════════════════════════════════════════════════════════════
# Egresos (R — recibidos)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Egresos":
    import pandas as pd

    st.title("Egresos — CFDIs recibidos")

    mes_actual = _today_mx().strftime("%Y-%m")
    col1, col2, col3 = st.columns(3)
    f_mes = col1.text_input("Mes (YYYY-MM)", value=mes_actual, key="egr_mes")
    f_dia = col2.text_input("Día específico YYYY-MM-DD (vacío = mes completo)", value="", key="egr_dia")
    f_rfc = col3.text_input("RFC", value=os.getenv("SAT_RFC", ""), key="egr_rfc")

    ctx = _context_base({"rfc_propietario": f_rfc, "empresa_id": f_rfc, "tipo": "R"})
    if f_dia.strip():
        ctx["dia"] = f_dia.strip()
    elif f_mes.strip():
        ctx["mes"] = f_mes.strip()

    with st.spinner("Cargando egresos..."):
        r = _run_skill("vertical_sat/sat_cfdi_list", ctx)

    if r.get("ok"):
        d = r.get("data", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Total recibidos",  d.get("total", 0))
        m2.metric("Monto total",      "${:,.2f}".format(d.get("monto_total", 0)))
        m3.metric("Tipo Egreso (E)",  d.get("total_egresos", 0))
        cfdis = d.get("cfdis", [])
        if cfdis:
            df   = pd.DataFrame(cfdis)
            cols = [c for c in ["fecha_emision", "uuid_cfdi", "rfc_emisor", "nombre_emisor",
                                 "tipo_comprobante", "total", "moneda", "forma_pago", "estado"]
                    if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Sin CFDIs recibidos para este periodo.")
    else:
        st.caption("sat_cfdi_list no disponible — " + r.get("error", ""))
